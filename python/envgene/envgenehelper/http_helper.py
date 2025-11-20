import requests

from python.envgene.envgenehelper.errors import IntegrationError


class ApiClient:

    def __init__(self, verify_ssl=False):
        self.verify_ssl = verify_ssl

    def get_json(self, url, headers=None, timeout=30):
        try:
            response = requests.get(
                url,
                headers=headers or {},
                verify=self.verify_ssl,
                timeout=timeout,
            )
            response.raise_for_status()
            return response.json()

        except requests.RequestException as e:
            raise IntegrationError(f"GET request failed for URL: {url}. Error: {e}")
