## NextLike is an open source item similarity & collaborative filtering recommendation engine

---

- Calculates items similarity vectors via the OpenAI embeddings API
- Uses pgvector to store & search items with similar vectors
- Uses Postgres for collaborative filtering recommendations
- [TODO] Automatically mixes collaborative with similarity recommendations when collaborative data are not enough to provide good recommendations

## Running locally

1. Copy the .env.example to .env and add your OpenAI api key
    
    `cp .env.example .env`
    
2. Run docker compose
    
    `docker compose up`
    
3. Check the API
    
    `curl http://localhost:8045/health`
    
    Should return `{"message":"Hi. I'm alive!"}`
    
4. Optionaly add the movielens dataset for experimentation
    
    `python scripts/load_movielens_dataset.py -d small`
    

## API usage

---

### Ingesting items (for similarity recommendations)

You can send up to 100.000 items in a single post request, the ingestion happens asyncronously via celery tasks. 

```python
requests.post("/api/items", json={
    "collection": "classifieds",
    "items": [
        {
            "id": 40172483,
            "fields": {
                "category": "Apartment -> Home -> Rent -> Real Estate",
                "area": 47,
                "price": 470,
                "offer_type": "rent"
            }
        },
        {
            "id": 40248423,
            "fields": {
                "category": "Detached Home -> Home -> Sale -> Real Estate",
                "area": 134.0,
                "price": 100000.0,
                "offer_type": "sale"
            }
        },
        {
            "id": 40451490,
            "fields": {
                "category": "Hotel -> Commercial -> Sale -> Real Estate",
                "area": 130.0,
                "price": 260000.0,
                "offer_type": "sale"
            }
        }
    ]
})
```

### Getting recommendations from similarity

```python
requests.post("/api/recommend", json={
    "collection": "classifieds",
    "config": {
        "similarity": {
            "similar_to_item_id": 40451490 ## similar to item with id=40451490
        }
    }
})

## OR

requests.post("/api/recommend", json={
    "collection": "classifieds",
    "config": {
        "similarity": {
            "similar_to_fields": {
                "category": "Hotel -> Commercial -> Sale -> Real Estate",
                "area": 100.0,
                "price": 200000.0,
                "offer_type": "sale"
            }
        }
    }
})
```

### Ingesting events (for collaborative filtering recommendations)

You can send up to 1 million events in a single post request, the ingestion happens asyncronously via celery tasks. 

```python
requests.post("/api/events", json={
    "collection": "classifieds",
    "events": [
        {
            "item_id": 40136315,
            "person_id": "3112779531605195",
            "event": "classified_view"
        },
        {
            "item_id": 40636186,
            "person_id": "3JAV8WT10U1FF49I",
            "event": "classified_view"
        },
        {
            "item_id": 40514326,
            "person_id": "EUI3UD9KLLPS9WZ8",
            "event": "classified_view"
        }
    ]
})
```

### Getting recommendations from collaborative filtering

```python
requests.post("/api/recommend", json={
    "collection": "classifieds",
    "config": {
        "collaborative": {
            "item_ids": [40136315]
        }
    }
})
```