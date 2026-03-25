# Distributed Task Processing Architecture

```mermaid
graph TD
    subgraph Producers["Producers"]
        API[API / Services]
    end

    subgraph RabbitMQ["RabbitMQ"]
        EX_TASK[task.exchange]
        EX_DLX[dlx.exchange]
        Q_MAIN[work.queue]
        Q_PRIORITY[priority.queue]
        Q_RETRY[retry.queue TTL]
        Q_DLQ[dead.letter.queue]
        EX_TASK --> Q_MAIN
        EX_TASK --> Q_PRIORITY
        Q_MAIN --> EX_DLX
        EX_DLX --> Q_DLQ
        Q_DLQ --> Q_RETRY
        Q_RETRY --> EX_TASK
    end

    subgraph Edge["Edge"]
        LB[Load Balancer]
    end

    subgraph Pool["Worker pool scales horizontally"]
        W1[Worker]
        W2[Worker]
        W3[Worker]
    end

    subgraph SQL["SQL tier"]
        PRIMARY[(Primary writes)]
        REPLICA[(Read replica)]
        PRIMARY -->|streaming replication| REPLICA
        REPLICA -.->|automatic promotion if primary fails| PRIMARY
    end

    subgraph Mon["Monitoring microservices"]
        HEALTH[Health checker]
        LOAD[Load monitor]
        ERR[Error logger]
    end

    subgraph Metrics["Observability"]
        PROM[Prometheus]
        GRAF[Grafana]
        PROM --> GRAF
    end

    API --> EX_TASK
    Q_MAIN --> W1
    Q_MAIN --> W2
    Q_MAIN --> W3
    Q_PRIORITY --> W1
    Q_PRIORITY --> W2
    Q_PRIORITY --> W3
    LB --> W1
    LB --> W2
    LB --> W3
    W1 --> PRIMARY
    W2 --> PRIMARY
    W3 --> REPLICA
    HEALTH --> PROM
    LOAD --> PROM
    ERR --> PROM
    W1 --> PROM
    W2 --> PROM
    W3 --> PROM
    LB --> PROM
    EX_TASK --> PROM
    PRIMARY --> PROM
    REPLICA --> PROM
```

## Design decisions

Task producers publish to a RabbitMQ exchange that fans out to a primary work queue and an optional priority queue so traffic shaping and SLAs stay in the broker layer. Messages that fail processing are routed through a dead-letter exchange into a dead-letter queue; automation or operators move work from the DLQ into a retry queue with TTL that re-publishes to the main exchange, giving bounded retries without blocking live consumers.

Workers scale horizontally: additional instances attach to the same queues and compete for messages. A load balancer sits in front of the worker tier for synchronous health, admin, or callback endpoints while asynchronous consumption still originates from RabbitMQ. Reads that can tolerate lag go to the read replica; writes go to the primary. When the primary fails, the replica is promoted automatically by the database platform or orchestrator so the system keeps a single writable leader.

Prometheus scrapes all long-lived components (workers, load balancer where exposed, RabbitMQ with its exporter, databases with exporters, and the three monitoring services). Grafana queries only Prometheus to keep one metrics source of truth. Splitting health checking, load monitoring, and error logging into small services keeps responsibilities isolated and lets teams scale or replace them independently.
