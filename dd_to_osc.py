"""Datadog monitor to OSC messages

This program reads the query from a Datadog monitor, calls their query API and normalizes 
the resultant values against the threshold to send out as an OSC message
"""
import argparse
import os
import time
import sys

from pprint import pprint
from pythonosc import udp_client


from datadog_api_client.v1 import ApiClient, Configuration
from datadog_api_client.v1.api import monitors_api, metrics_api

# from datadog_api_client.v1.models import *


def get_points(api_instance, query, scope, start_time, end_time):
    # Query timeseries points
    query_api_response = api_instance.query_metrics(start_time, end_time, query)
    query_api_response_dict = query_api_response.to_dict()
    metric_series = query_api_response_dict.get("series")
    points = list()
    scopes = set()
    valid_series = list()
    for series in metric_series:
        series_scope = series.get("scope")
        scopes.add(series_scope)
        if scope and series_scope != scope:
            continue
        valid_series.append(series)
    series_points = valid_series[-1].get("pointlist")
    for point in series_points:
        if not point[-1]:
            continue
        if point[-1] < 0:
            print("negative metrics currently unsupported")
            sys.exit(1)
        points.append(point)

    if len(scopes) > 1 and not scope:
        print("Multiple scopes found.")
        pprint(scopes)
        print("Must pass a scope via --scope or the environment variable DATADOG_SCOPE")
        sys.exit(1)

    return points


def get_minimum(points):
    minimum = sys.float_info.max
    for point in points:
        if not point[1]:
            continue
        if point[1] < minimum:
            minimum = point[1]
    return minimum


def get_maximum(points):
    maximum = sys.float_info.min
    for point in points:
        if not point[1]:
            continue
        if point[1] > maximum:
            maximum = point[1]
    return maximum


def get_average(points):
    total = 0
    count = 0
    for point in points:
        if not point[1]:
            continue
        total += point[1]
        count += 1
    return total / float(count)


def get_monitor_points(api_instance, query, scope, evaluation_function):
    end_time = int(
        time.time()
    )  # int | End of the queried time period, seconds since the Unix epoch.
    start_time = (
        end_time - time_modifier
    )  # int | Start of the queried time period, seconds since the Unix epoch.

    points = get_points(api_instance, query, scope, start_time, end_time)
    evaluation = None
    if evaluation_function == "avg":
        evaluation = get_average(points)
    else:
        print("only average thresholds currently supported")
        sys.exit(1)
    return evaluation


def get_monitor_state(monitor_api_instance, monitor_id):
    monitor_api_response = monitor_api_instance.get_monitor(monitor_id)
    monitor_response_dict = monitor_api_response.to_dict()
    return monitor_response_dict.get("overall_state")


# Defining the host is optional and defaults to https://api.datadoghq.com
# See configuration.py for a list of all supported configuration parameters.
configuration = Configuration(
    host="https://api.{}".format(os.getenv("DATADOG_SITE", "datadoghq.com"))
)

# The client must configure the authentication and authorization parameters
# in accordance with the API server security policy.
# Examples for each auth method are provided below, use the example that
# satisfies your auth use case.

# Configure API key authorization: apiKeyAuth
configuration.api_key["apiKeyAuth"] = os.getenv("DATADOG_API_KEY")

# Configure API key authorization: appKeyAuth
configuration.api_key["appKeyAuth"] = os.getenv("DATADOG_APP_KEY")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--ip", default=None, help="The ip of the OSC server")
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="The port the OSC server is listening on.",
    )
    parser.add_argument(
        "--monitor", type=int, default=None, help="The Datadog monitor to monitor"
    )
    parser.add_argument(
        "--scope", type=str, default=None, help="A scope for the monitor"
    )
    parser.add_argument(
        "--value", type=str, default=None, help="OSC channel to send values to"
    )
    parser.add_argument(
        "--threshold",
        type=str,
        default=None,
        help="OSC channel to send threshold alerts to",
    )

    args = parser.parse_args()

    MONITOR = None
    if os.getenv("DATADOG_MONITOR"):
        MONITOR = int(os.getenv("DATADOG_MONITOR"))

    if args.monitor:
        MONITOR = args.monitor

    if not MONITOR:
        print(
            "Must pass a monitor to monitor via --monitor or \
            an environment variable named DATADOG_MONITOR"
        )
        sys.exit(1)

    SCOPE = None
    if os.getenv("DATADOG_SCOPE"):
        SCOPE = os.getenv("DATADOG_SCOPE")

    if args.scope:
        SCOPE = args.scope

    OSC_IP = "127.0.0.1"
    if os.getenv("OSC_IP"):
        OSC_IP = os.getenv("OSC_IP")

    if args.ip:
        OSC_IP = args.ip

    OSC_PORT = 7001
    if os.getenv("OSC_PORT"):
        OSC_PORT = int(os.getenv("OSC_PORT"))

    if args.port:
        OSC_PORT = args.port

    OSC_VALUE_CHANNEL = "/ch/1"
    if os.getenv("OSC_VALUE_CHANNEL"):
        OSC_VALUE_CHANNEL = os.getenv("OSC_VALUE_CHANNEL")

    if args.value:
        OSC_VALUE_CHANNEL = args.value

    OSC_THRESHOLD_CHANNEL = "/ch/2"
    if os.getenv("OSC_VALUE_CHANNEL"):
        OSC_VALUE_CHANNEL = os.getenv("OSC_VALUE_CHANNEL")

    if args.value:
        OSC_VALUE_CHANNEL = args.value

    # Enter a context with an instance of the API client
    with ApiClient(configuration) as api_client:
        monitor_api_instance = monitors_api.MonitorsApi(api_client)

        # Get a monitor's details
        monitor_api_response = monitor_api_instance.get_monitor(MONITOR)
        monitor_response_dict = monitor_api_response.to_dict()
        monitor_query_string = monitor_response_dict.get("query")
        if "anomalie" in monitor_query_string:
            print("anomalie metrics not currently supported")
            sys.exit(1)
        monitor_query_split = monitor_query_string.split(" ")
        monitor_query = " ".join(monitor_query_split[:-2])
        query_split = monitor_query.split(":")
        query = ":".join(query_split[1:])
        evaluation_query_split = query_split[0].split("(")
        evaluation_function = evaluation_query_split[0]
        evaluation_period = evaluation_query_split[1][:-1].split("_")[-1]
        comparitor = monitor_query_split[-2]
        if comparitor != ">":
            print("only > threshold monitors currently supported")
            sys.exit(1)
        threshold = (
            monitor_response_dict.get("options").get("thresholds").get("critical")
        )
        time_modifier = 60  # 1 minute
        if evaluation_period[-1] == "h":
            time_modifier *= 60
        time_modifier *= int("".join(evaluation_period[:-1]))
        metrics_api_instance = metrics_api.MetricsApi(api_client)

        client = udp_client.SimpleUDPClient(OSC_IP, OSC_PORT)

        while True:
            evaluation = get_monitor_points(
                metrics_api_instance, query, SCOPE, evaluation_function
            )
            normalzied_evaluation = evaluation / threshold
            if normalzied_evaluation > 1:
                normalzied_evaluation = 1
            pprint(normalzied_evaluation)
            monitor_state = get_monitor_state(monitor_api_instance, MONITOR)
            alerting = monitor_state == "Alert"
            print("alerting: {}".format(alerting))
            print("sending {} to value".format(normalzied_evaluation))
            client.send_message(OSC_VALUE_CHANNEL, normalzied_evaluation)
            print("sending {} to threshold".format(int(alerting)))
            client.send_message(OSC_THRESHOLD_CHANNEL, int(alerting))
            time.sleep(5)
