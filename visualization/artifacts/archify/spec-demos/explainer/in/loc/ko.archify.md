# Why does a cache miss add latency? {#cache-miss}

The API asks Redis first, so a miss costs **one extra round trip** before the database is queried.[](source:router)

- The cache check happens before every database read.
- A miss returns nil, and only then the API queries the database.

@answer scope="Order API · single Redis node"
@meta locale=ko
@source router title="Request handler" path=archify/explainer/layout.mjs lines=1:5
@source docs title="Redis docs" url=https://redis.io/docs

## What happens on a miss? {#flow}

@sequence id=miss-flow title="Cache miss"
| actor api | Order API | backend |
| actor redis | Redis | database |
| actor db | Database | database |
| api | redis | GET order:42 |
| redis | api | nil | return |
| api | db | SELECT order 42 | emphasis |

@steps id=miss-steps
| ask | Ask Redis | Look up the key first. | miss-flow | api |
| fallback | Read database | Run only after nil. | miss-flow | db |

## Which option fits? {#options}

| Criterion | Cache-aside | Write-through |
| --- | --- | --- |
| Read latency | Low {good:Fast} | Low |
| Write cost | Low | High {bad:Slow} |

## What should you check? {#checks}

@facts
| TTL | 60 s |
| Hit rate | measured per day |

@callout level=warning title="Stale reads"
A hit can return data older than the database.

- [ ] Confirm the TTL
- [ ] Watch the hit rate
