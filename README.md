## NextLike is an open source item similarity & collaborative filtering recommendation engine

---

- Calculates items similarity vectors via the OpenAI embeddings API
- Uses pgvector to store & search items with similar vectors
- Uses Postgres for collaborative filtering recommendations
- Automatically mixes collaborative with similarity recommendations when collaborative data are not enough to
  provide good recommendations
- [TODO] Image similarity using LLaVA to describe an image

## Running locally

1. Copy the .env.example to .env and add your OpenAI api key

   `cp .env.example .env`

2. Run docker compose

   `docker compose up`

3. Check the API

   `curl http://localhost:8045/health`

   Should return `{"message":"Hi. I'm alive!"}`

## API usage

---

### Ingesting items

You can send up to 100k items in a single post request, the ingestion happens asyncronously via celery tasks.

```python
requests.post("/api/items", json={
    "collection": "classifieds",
    "items": [
        {
            "id": "40172483",
            "fields": {
                "category": "Apartment -> Home -> Rent -> Real Estate",
                "area": 47,
                "price": 470,
                "offer_type": "rent"
            }
        },
        {
            "id": "40248423",
            "fields": {
                "category": "Detached Home -> Home -> Sale -> Real Estate",
                "area": 134.0,
                "price": 100000.0,
                "offer_type": "sale"
            },
           "description":"Area is 134, price is 10000, offertype is sale"
        },
        {
            "id": "40451490",
            "fields": {
                "category": "Hotel -> Commercial -> Sale -> Real Estate",
                "area": 130.0,
                "price": 260000.0,
                "offer_type": "sale"
            },
            "description_from_fields": ["area","price","offer_type"]
        }
    ]
})
```

### Ingesting events

You can send up to 1 million events in a single post request, the ingestion happens asyncronously via celery tasks.

```python
requests.post("/api/events", json={
    "collection": "classifieds",
    "events": [
        {
            "item": "40136315",
            "person": "3112779531605195",
            "event": "classified_view"
        },
        {
            "item": "40636186",
            "person": "3JAV8WT10U1FF49I",
            "event": "classified_view"
        },
        {
            "item": "40514326",
            "person": "EUI3UD9KLLPS9WZ8",
            "event": "classified_view"
        }
    ]
})
```

### Getting recommendations from similarity

```python
requests.post("/api/search", json={
    "collection": "classifieds",
    "config": {
        "similar": {
            "of": [
                ## Get items similar to item 40612658
                {
                    "item": ["40612658"],
                    "weight": 0.5  ## The weight of the clause in the final score
                },
                ## Get items similar to items that a user has seen in the last month
                {
                    "person": "person1",
                    "time": "1M",
                    "weight": 0.1  ## The weight of the clause in the final score
                },
                ## Get items with similar fields
                {
                    "fields": {
                        "price": 1000,
                        "area": 100,
                        "category": "Apartment -> Home -> Rent -> Real Estate",
                    },
                    "weight": 0.1  ## The weight of the clause in the final score
                },
                ## Get items by prompt
                {
                    "prompt": "A cheap 2 bedroom apartment",
                    "weight": 0.1  ## The weight of the clause in the final score
                }
            ]
        },
        "limit": 10,
        "for_person": "person1"
    }
})
```

### Get collaborative recommendations

```python
requests.post("/api/search", json={
    "collection": "classifieds",
    "config": {
        "collaborative": {
            "of": [
                ## Get items other users has seen along with the provided item
                {
                    "item": ["40612658"]
                },
                ## Get items other users has seen along with the items the provided person has seen in the last day
                {
                    "person": "person1",
                    "time": "1d"
                }
            ]
        },
        "limit": 10,
        "for_person": "person1"
    }
})
```

### Get combined recommendations
For now the similar items are just filling the collaborative until the limit has been reached.

```python
requests.post("/api/search", json={
    "collection": "classifieds",
    "config": {
        "similar": {
            "of": [
                {
                    "person": "person1",
                    "time": "1d"
                }
            ]
        },
        "collaborative": {
            "of": [
                {
                    "person": "person1",
                    "time": "1d"
                }
            ]
        },
        "limit": 10,
        "for_person": "person1"
    }
})
```

### Filter recommendations

```python
requests.post("/api/search", json={
    "collection": "classifieds",
    "config": {
        "similar": {
            "of": [
                {
                    "person": "person1",
                    "time": "1d"
                }
            ]
        },
        "filter": {
            "offertype": "sale",
            "price": {
                "gte": 1000
            },
            "not": {
                "area": {
                    "gte": 200
                }
            },
            "category_ids": {
                "contains": 15001
            }
        },
        "limit": 10,
        "for_person": "person1"
    }
})
```

### Exclude items

```python
requests.post("/api/search", json={
    "collection": "classifieds",
    "config": {
        "similar": {
            "of": [
                {
                    "person": "person1",
                    "time": "1d"
                }
            ]
        },
        "exclude": [
            ## exclude item with the provided id
            {
                "item": ["40612658"]
            },
            ## exclude the last 100 items that the user has already interacted with in the last 7 days
            {
                "person": "person2",
                "limit": 100,
                "time": "7d"
            }
        ],
        "limit": 10,
        "for_person": "person1"
    }
})
```

### Feed like recommendations

Each recommendation returns a new set of items that have not already been recommended to the user.

```python
requests.post("/api/search", json={
    "collection": "classifieds",
    "config": {
        "similar": {
            "of": [
                {
                    "person": "person1",
                    "time": "1d"
                }
            ]
        },
        "limit": 10,
        "feedlike":True,
        "for_person": "person1"
    }
})
```
