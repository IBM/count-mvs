import requests


class API:

    def __init__(self) -> None:
        self.host = "api"

    def set_start_search_failure(self, status_code) -> None:
        resp = requests.post(
            f"https://{self.host}/conf/route_configs/start_search",
            json={"status_code": status_code})

        if not resp.ok or resp.status_code != 200:
            raise Exception("Failed to set start search to failure")

    def set_start_search_success(self) -> None:
        resp = requests.post(
            f"https://{self.host}/conf/route_configs/start_search",
            json={"status_code": 200})

        if not resp.ok or resp.status_code != 200:
            raise Exception("Failed to set start search to success")

    def set_search_results_failure(self, status_code) -> None:
        resp = requests.post(f"https://{self.host}/conf/route_configs/results",
                             json={"status_code": status_code})

        if not resp.ok or resp.status_code != 200:
            raise Exception("Failed to set get search results to failure")

    def set_search_results_success(self) -> None:
        resp = requests.post(f"https://{self.host}/conf/route_configs/results",
                             json={"status_code": 200})

        if not resp.ok or resp.status_code != 200:
            raise Exception("Failed to set get search results to success")

    def set_search_status_failure(self, status_code) -> None:
        resp = requests.post(f"https://{self.host}/conf/route_configs/status",
                             json={"status_code": status_code})

        if not resp.ok or resp.status_code != 200:
            raise Exception("Failed to set get search status to failure")

    def set_search_status_success(self) -> None:
        resp = requests.post(f"https://{self.host}/conf/route_configs/status",
                             json={"status_code": 200})

        if not resp.ok or resp.status_code != 200:
            raise Exception("Failed to set get search status to success")

    def set_search_data(self, data) -> None:
        resp = requests.post(f"https://{self.host}/conf/search_data",
                             json=data)

        if not resp.ok or resp.status_code != 200:
            raise Exception("Failed to set search data")
