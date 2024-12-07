class RealEstateSearchDataset(object):
    def get_aggregation_location_items(self):
        return [
            {
                "id": "location_athens",
                "fields": {
                    "field": "location",
                    "value": "athens"
                },
                "description": "athens"
            },
            {
                "id": "location_thessaloniki",
                "fields": {
                    "field": "location",
                    "value": "thessaloniki"
                },
                "description": "thessaloniki"
            },
            {
                "id": "location_patra",
                "fields": {
                    "field": "location",
                    "value": "patra"
                },
                "description": "patra"
            },
            {
                "id": "location_heraklion",
                "fields": {
                    "field": "location",
                    "value": "heraklion"
                },
                "description": "heraklion"
            },
            {
                "id": "location_larisa",
                "fields": {
                    "field": "location",
                    "value": "larisa"
                },
                "description": "larisa"
            },
            {
                "id": "location_volos",
                "fields": {
                    "field": "location",
                    "value": "volos"
                },
                "description": "volos"
            },
            {
                "id": "location_ioannina",
                "fields": {
                    "field": "location",
                    "value": "ioannina"
                },
                "description": "ioannina"
            },
            {
                "id": "location_irakleio",
                "fields": {
                    "field": "location",
                    "value": "irakleio"
                },
                "description": "irakleio"
            },
            {
                "id": "location_kavala",
                "fields": {
                    "field": "location",
                    "value": "kavala"
                },
                "description": "kavala"
            },
            {
                "id": "location_chania",
                "fields": {
                    "field": "location",
                    "value": "chania"
                },
                "description": "chania"
            },
            {
                "id": "location_rhodes",
                "fields": {
                    "field": "location",
                    "value": "rhodes"
                },
                "description": "rhodes"
            },
            {
                "id": "location_corfu",
                "fields": {
                    "field": "location",
                    "value": "corfu"
                },
                "description": "corfu"
            },
        ]

    def get_aggregation_category_items(self):
        return [
            {
                "id": "category_home",
                "fields": {
                    "field": "category",
                    "value": "home"
                },
                "description": "home"
            },
            {
                "id": "category_apartment",
                "fields": {
                    "field": "category",
                    "value": "apartment"
                },
                "description": "apartment"
            },
            {
                "id": "category_office",
                "fields": {
                    "field": "category",
                    "value": "office"
                },
                "description": "office"
            },
            {
                "id": "category_plot",
                "fields": {
                    "field": "category",
                    "value": "plot"
                },
                "description": "plot"
            }
        ]

    def get_aggregation_seller_type_items(self):
        return [
            {
                "id": "seller_type_owner",
                "fields": {
                    "field": "seller_type",
                    "value": "owner"
                },
                "description": "owner"
            },
            {
                "id": "seller_type_agency",
                "fields": {
                    "field": "seller_type",
                    "value": "agency"
                },
                "description": "agency"
            }
        ]

    def get_aggregation_heating_type_items(self):
        return [
            {
                "id": "heating_type_central",
                "fields": {
                    "field": "heating_type",
                    "value": "central"
                },
                "description": "central"
            },
            {
                "id": "heating_type_autonomous",
                "fields": {
                    "field": "heating_type",
                    "value": "autonomous"
                },
                "description": "autonomous"
            },
            {
                "id": "heating_type_none",
                "fields": {
                    "field": "heating_type",
                    "value": "none"
                },
                "description": "none"
            },
            {
                "id": "heating_type_air_condition",
                "fields": {
                    "field": "heating_type",
                    "value": "air_condition"
                },
                "description": "air condition"
            },
            {
                "id": "heating_type_fireplace",
                "fields": {
                    "field": "heating_type",
                    "value": "fireplace"
                },
                "description": "fireplace"
            }
        ]

    def get_aggregation_tags_items(self):
        return [
            {
                "id": "tags_new",
                "fields": {
                    "field": "tags",
                    "value": "new"
                },
                "description": "new"
            },
            {
                "id": "tags_furnished",
                "fields": {
                    "field": "tags",
                    "value": "furnished"
                },
                "description": "furnished"
            },
            {
                "id": "tags_elevator",
                "fields": {
                    "field": "tags",
                    "value": "elevator"
                },
                "description": "elevator"
            },
            {
                "id": "tags_parking",
                "fields": {
                    "field": "tags",
                    "value": "parking"
                },
                "description": "parking"
            },
            {
                "id": "tags_storage",
                "fields": {
                    "field": "tags",
                    "value": "storage"
                },
                "description": "storage"
            },
            {
                "id": "tags_garden",
                "fields": {
                    "field": "tags",
                    "value": "garden"
                },
                "description": "garden"
            },
            {
                "id": "tags_sea_view",
                "fields": {
                    "field": "tags",
                    "value": "sea_view"
                },
                "description": "sea_view"
            },
            {
                "id": "tags_mountain_view",
                "fields": {
                    "field": "tags",
                    "value": "mountain_view"
                },
                "description": "mountain_view"
            },
            {
                "id": "tags_city_view",
                "fields": {
                    "field": "tags",
                    "value": "city_view"
                },
                "description": "city_view"
            },
            {
                "id": "tags_investment",
                "fields": {
                    "field": "tags",
                    "value": "investment"
                },
                "description": "investment"
            },
            {
                "id": "tags_luxury",
                "fields": {
                    "field": "tags",
                    "value": "luxury"
                },
                "description": "luxury"
            }
        ]

    def get_aggregation_items(self):
        return self.get_aggregation_category_items() + self.get_aggregation_seller_type_items() + self.get_aggregation_heating_type_items() + self.get_aggregation_tags_items() + self.get_aggregation_location_items()

    def get_query_items(self):
        return [
            # {
            #     "id": "query_apartment_athens_price_10000_20000",
            #     "fields": {
            #         "category": "apartment",
            #         "location": "athens",
            #         "price_from": 10000,
            #         "price_to": 20000,
            #     },
            #     "description": "apartment in athens, from 10000 euros to 20000"
            # },
            {
                "id": "query_apartment_athens",
                "fields": {
                    "category": "apartment",
                    "location": "athens"
                },
                "description": "apartment in athens"
            },
            {
                "id": "query_office_thessaloniki",
                "fields": {
                    "category": "office",
                    "location": "thessaloniki"
                },
                "description": "office_thessaloniki"
            },
            {
                "id": "query_home_patra",
                "fields": {
                    "category": "home",
                    "location": "patra"
                },
                "description": "home_patra"
            },
            {
                "id": "rent_appartment",
                "fields": {
                    "offertype": "rent",
                    "category": "apartment"
                },
                "description": "rent apartment"
            }
        ]

    def get_aggregation_config(self):
        return {
            "name": "test_aggregation",
            "fields": {
                "category": {
                    "type": "item",
                    "description": "the category of the ad",
                    "search": {
                        "similar": {
                            "of": [
                                {
                                    "text": "$query"
                                }
                            ]
                        },
                        "filter": {
                            "field": "category"
                        },
                        "export": "value",
                        "cache": None,
                        "limit": 1
                    }
                },
                "construction_year": {
                    "type": "integer",
                    "description": "the year of construction",
                },
                "price_from": {
                    "type": "integer",
                    "description": "the price from",
                },
                "offertype": {
                    "type": "text",
                    "enum": ["rent", "sale"],
                    "description": "the offer type",
                },
                "price_to": {
                    "type": "integer",
                    "description": "the price to",
                },
                "area_from": {
                    "type": "integer",
                    "description": "the area in sqm",
                },
                "area_to": {
                    "type": "integer",
                    "description": "the area in sqm",
                },
                "location": {
                    "type": "item",
                    "multiple": True,
                    "description": "the location",
                    "search": {
                        "similar": {
                            "of": [
                                {
                                    "text": "$query"
                                }
                            ]
                        },
                        "filter": {
                            "field": "location"
                        },
                        "export": "value",
                        "cache": None,
                        "limit": 1
                    }
                },
                "seller_type": {
                    "type": "item",
                    "description": "the seller type",
                    "search": {
                        "similar": {
                            "of": [
                                {
                                    "text": "$query"
                                }
                            ]
                        },
                        "filter": {
                            "field": "seller_type"
                        },
                        "export": "value",
                        "cache": None,
                        "limit": 1
                    }
                },
                "heating_type": {
                    "type": "item",
                    "description": "the heating type",
                    "search": {
                        "similar": {
                            "of": [
                                {
                                    "text": "$query"
                                }
                            ]
                        },
                        "filter": {
                            "field": "heating_type"
                        },
                        "export": "value",
                        "cache": None,
                        "limit": 1
                    }
                },
                "tags": {
                    "type": "item",
                    "description": "the tags of the ad",
                    "search": {
                        "similar": {
                            "of": [
                                {
                                    "prompt": "$query"
                                }
                            ]
                        },
                        "filter": {
                            "field": "tags"
                        },
                        "export": "value",
                        "cache": None,
                        "limit": 1
                    }
                }
            }
        }
