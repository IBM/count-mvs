"""
Copyright 2022 IBM Corporation All Rights Reserved.
SPDX-License-Identifier: Apache-2.0
"""

import requests


def _handle_err(resp, status_code, msg) -> None:
    if not resp.ok or resp.status_code != status_code:
        raise Exception(msg)


class API:

    def __init__(self) -> None:
        self.host = "api"

    def reset(self) -> None:
        resp = requests.post(f"https://{self.host}/conf/reset")
        _handle_err(resp, 200, "Failed to reset the mock API")

    def set_about(self, status_code) -> None:
        resp = requests.post(f"https://{self.host}/conf/route_configs/about", json={"status_code": status_code})
        _handle_err(resp, 200, "Failed to set about to {status_code}")

    def set_start_search_failure(self, status_code) -> None:
        resp = requests.post(f"https://{self.host}/conf/route_configs/start_search", json={"status_code": status_code})
        _handle_err(resp, 200, "Failed to set start search to failure")

    def set_start_search_success(self) -> None:
        resp = requests.post(f"https://{self.host}/conf/route_configs/start_search", json={"status_code": 200})
        _handle_err(resp, 200, "Failed to set start search to success")

    def set_search_results_failure(self, status_code) -> None:
        resp = requests.post(f"https://{self.host}/conf/route_configs/results", json={"status_code": status_code})
        _handle_err(resp, 200, "Failed to set get search results to failure")

    def set_search_results_success(self) -> None:
        resp = requests.post(f"https://{self.host}/conf/route_configs/results", json={"status_code": 200})
        _handle_err(resp, 200, "Failed to set get search results to success")

    def set_search_status_failure(self, status_code) -> None:
        resp = requests.post(f"https://{self.host}/conf/route_configs/status", json={"status_code": status_code})
        _handle_err(resp, 200, "Failed to set get search status to failure")

    def set_search_status_success(self) -> None:
        resp = requests.post(f"https://{self.host}/conf/route_configs/status", json={"status_code": 200})
        _handle_err(resp, 200, "Failed to set get search status to success")

    def add_search_data(self, data) -> None:
        resp = requests.post(f"https://{self.host}/conf/add_search_data", json=data)
        _handle_err(resp, 200, "Failed to set search data")
