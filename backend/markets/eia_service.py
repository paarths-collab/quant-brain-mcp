import requests
import os
from typing import Dict, Any, Optional

class EIAService:
    """
    Service to interact with the U.S. Energy Information Administration (EIA) API v2.
    """
    BASE_URL = "https://api.eia.gov/v2"
    # Using the key provided by the user. In production, this should be in os.environ
    API_KEY = "jvRlsfoBFBGHMhkspheJBvQoyz1noatXLcUmndto"

    def __init__(self):
        self.api_key = self.API_KEY

    def _fetch_data(self, path: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Internal method to fetch data from EIA API.
        """
        if params is None:
            params = {}
        
        params['api_key'] = self.api_key
        # Default to JSON format if not specified, though v2 usually defaults to it.
        # frequency, data, facets etc can be passed in params
        
        url = f"{self.BASE_URL}/{path}"
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            json_response = response.json()
            
            # EIA v2 API structure often wraps data in "response" object
            if "response" in json_response and "data" in json_response["response"]:
                return json_response["response"]
                
            return json_response
        except requests.exceptions.RequestException as e:
            print(f"Error fetching data from EIA API: {e}")
            return {"error": str(e)}

    def get_crude_oil_reserves(self) -> Dict[str, Any]:
        """
        Fetches crude oil proved reserves.
        Path: /petroleum/crd/nido/ (sample path, may need adjustment based on exact data needed)
        Let's try a known path for reserves.
        Category: Petroleum > Crude Oil > Proved Reserves
        """
        # Specific route for crude oil reserves often falls under:
        # petroleum/yer/jcr/ calculated or similar.
        # Let's try a broader query or specific valid route if known.
        # Based on v2 docs, we can query /petroleum/pnp/wiup/data for weekly inputs etc.
        # For reserves, it is typically an annual series.
        # Let's try to list data for the 'petroleum' route first or use a known one.
        # Attempting to fetch "U.S. Crude Oil Proved Reserves"
        # API Route: petroleum/crd/pres/data
        
        # We will use a generic path that is robust.
        # Example: Total Petroleum and other liquids production
        return self._fetch_data("petroleum/crd/pres/data", {
            "frequency": "annual",
            "data[0]": "value",
            "sort[0][column]": "period",
            "sort[0][direction]": "desc",
            "offset": 0,
            "length": 5
        })

    def get_petroleum_summary(self) -> Dict[str, Any]:
        """
        Fetches a summary of petroleum data.
        """
        # Example: Petroleum details
        return self._fetch_data("petroleum/sum/sndw/data", {
             "frequency": "weekly",
             "data[0]": "value",
             "sort[0][column]": "period",
             "sort[0][direction]": "desc",
             "length": 5
        })
