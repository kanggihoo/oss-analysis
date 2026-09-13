# DBHub Overview

<details>
<summary>Relevant source files</summary>

The following files were used as context for generating this wiki page:

- [.github/workflows/npm-publish.yml](.github/workflows/npm-publish.yml)
- [README.md](README.md)
- [package.json](package.json)
- [src/index.ts](src/index.ts)

</details>



This document provides a technical overview of DBHub, a universal database gateway implementing the Model Context Protocol (MCP) server interface. For installation guidance, see [Installation and Quick Start](#1.1). For architectural details, see [Architecture Overview](#1.2).

## What is DBHub?

DBHub is a bridge between MCP-compatible clients (like Claude Desktop and Cursor) and various database systems. It allows AI assistants to connect to, query, and explore databases without requiring specific database adapter implementations for each client.

```mermaid
flowchart TB
    subgraph "MCP Clients"
        Claude["Claude Desktop"]
        Cursor["Cursor"]
        Other["Other MCP Clients"]
    end
    
    subgraph "DBHub"
        Server["MCP Server Implementation"]
        
        subgraph "Transport Layer"
            STDIO["STDIO Transport"]
            SSE["SSE Transport"]
        end
        
        subgraph "Core Components"
            Resources["Resource Endpoints"]
            Tools["Tool Implementations"]
            Prompts["Prompt Handlers"]
        end
        
        subgraph "Connector System"
            ConnMgr["ConnectorManager"]
            ConnReg["ConnectorRegistry"]
            Connectors["Database Connectors"]
        end
    end
    
    subgraph "Database Systems"
        PostgreSQL[(PostgreSQL)]
        SQLServer[(SQL Server)]
        MySQL[(MySQL)]
        MariaDB[(MariaDB)]
        SQLite[(SQLite)]
    end
    
    Claude --> STDIO --> Server
    Cursor --> STDIO & SSE --> Server
    Other --> STDIO & SSE --> Server
    
    Server --> Resources & Tools & Prompts
    
    Resources & Tools & Prompts --> ConnMgr
    ConnMgr --> ConnReg
    ConnReg --> Connectors
    
    Connectors --> PostgreSQL & SQLServer & MySQL & MariaDB & SQLite
```

Sources: [README.md:9-27]()

## Key Features

DBHub provides a unified interface for database interaction with the following capabilities:

- **Universal Database Gateway**: Connect to PostgreSQL, SQL Server, MySQL, MariaDB, and SQLite databases
- **MCP Server Implementation**: Compliant with the Model Context Protocol for AI interaction
- **Structured Resource Endpoints**: Navigate database schemas, tables, indexes, and procedures
- **Database Tools**: Execute queries and list available connectors
- **AI-Assisted Capabilities**: Generate SQL and explain database elements through prompts
- **Flexible Transport Options**: Support for both STDIO and SSE (HTTP-based) transport protocols
- **Demo Mode**: Built-in sample employee database for testing without external configuration

Sources: [README.md:9-27](), [README.md:35-61]()

## System Architecture

The DBHub codebase has a modular architecture with several key components:

```mermaid
classDiagram
    class index {
        main()
    }
    
    class server {
        main()
        createServer()
        setupStdioTransport()
        setupSSETransport()
    }
    
    class ConnectorManager {
        -activeConnector: Connector
        -connected: boolean
        +connectWithDSN(dsn)
        +disconnect()
        +getConnector()
        +isConnected()
        +getCurrentConnector()
    }
    
    class ConnectorRegistry {
        -connectors: Map
        +register(connector)
        +getConnector(id)
        +getConnectorForDSN(dsn)
        +getAvailableConnectors()
    }
    
    class Connector {
        <<interface>>
        +id: string
        +name: string
        +connect(dsn)
        +disconnect()
        +getSchemas()
        +getTables(schema)
        +getTableSchema(tableName, schema)
        +executeQuery(query)
    }
    
    class PostgresConnector {
        implements Connector
    }
    
    class SQLServerConnector {
        implements Connector
    }
    
    class MySQLConnector {
        implements Connector
    }
    
    class MariaDBConnector {
        implements Connector
    }
    
    class SQLiteConnector {
        implements Connector
    }
    
    index --> server: imports
    server --> ConnectorManager: uses
    ConnectorManager --> ConnectorRegistry: uses
    ConnectorRegistry --> Connector: manages
    Connector <|.. PostgresConnector
    Connector <|.. SQLServerConnector
    Connector <|.. MySQLConnector
    Connector <|.. MariaDBConnector
    Connector <|.. SQLiteConnector
```

**Main Components:**

1. **Entry Point** (`index.ts`): Bootstraps the application and loads connectors
2. **Server** (`server.ts`): Sets up the MCP server and transport layers
3. **Connector System**: Manages database connections through a unified interface
   - `ConnectorManager`: Handles the active database connection
   - `ConnectorRegistry`: Registers and retrieves available connectors
   - `Connector` interface: Common API implemented by all database connectors
4. **Database Connectors**: Implement database-specific functionality
5. **Resource Endpoints**: Expose database structure in a RESTful format
6. **Tools**: Implement functionality like query execution
7. **Prompts**: Handle AI-assisted features like SQL generation

Sources: [src/index.ts:1-20](), [README.md:11-26]()

## Supported Database Features

DBHub exposes database capabilities organized into resources, tools, and prompts.

### Database Resources

| Resource | URI Format | Description |
|----------|------------|-------------|
| Schemas | `db://schemas` | List of available database schemas |
| Tables | `db://schemas/{schemaName}/tables` | Tables within a schema |
| Table Structure | `db://schemas/{schemaName}/tables/{tableName}` | Column definitions for a table |
| Indexes | `db://schemas/{schemaName}/tables/{tableName}/indexes` | Indexes for a table |
| Procedures | `db://schemas/{schemaName}/procedures` | Stored procedures in a schema |
| Procedure Details | `db://schemas/{schemaName}/procedures/{procedureName}` | Details of a stored procedure |

### Database Tools

| Tool | Command | Description |
|------|---------|-------------|
| Execute Query | `run_query` | Run SQL queries against the connected database |
| List Connectors | `list_connectors` | List available database connectors |

### Prompt Capabilities

| Prompt | Command | Description |
|--------|---------|-------------|
| Generate SQL | `generate_sql` | AI-assisted SQL query generation |
| Explain DB Elements | `explain_db` | AI-assisted explanation of database elements |

Sources: [README.md:35-61]()

## Connection and Transport Mechanisms

DBHub supports multiple connection methods and transport protocols:

### Database Connections

Connections to databases are managed through Database Source Names (DSNs):

```mermaid
flowchart TD
    Start([Start DBHub]) --> Config["Load Configuration"]
    Config --> DSNCheck{"DSN Specified?"}
    DSNCheck -->|Yes| ParseDSN["Parse DSN"]
    DSNCheck -->|No| DemoCheck{"Demo Mode?"}
    DemoCheck -->|Yes| LoadDemo["Load Demo Database"]
    DemoCheck -->|No| ExitError["Exit with Error"]
    ParseDSN --> SelectConnector["Select Appropriate Connector"]
    LoadDemo --> SelectConnector
    SelectConnector --> Connect["Connect to Database"]
    Connect --> StartServer["Start MCP Server"]
```

Supported DSN formats:

| Database | DSN Format | Example |
|----------|------------|---------|
| PostgreSQL | `postgres://[user]:[password]@[host]:[port]/[database]` | `postgres://user:pass@localhost:5432/dbname?sslmode=disable` |
| MySQL | `mysql://[user]:[password]@[host]:[port]/[database]` | `mysql://user:pass@localhost:3306/dbname` |
| MariaDB | `mariadb://[user]:[password]@[host]:[port]/[database]` | `mariadb://user:pass@localhost:3306/dbname` |
| SQL Server | `sqlserver://[user]:[password]@[host]:[port]/[database]` | `sqlserver://user:pass@localhost:1433/dbname` |
| SQLite | `sqlite:///[path/to/file]` or `sqlite::memory:` | `sqlite:///path/to/database.db` or `sqlite::memory:` |

### Transport Protocols

DBHub supports two transport protocols for client communication:

1. **STDIO** (Standard I/O): Default transport, used by Claude Desktop
2. **SSE** (Server-Sent Events): HTTP-based transport, used by web clients and Cursor

```mermaid
flowchart LR
    subgraph "Transport Options"
        STDIO["STDIO Transport\n(Default)"]
        SSE["SSE Transport\n(HTTP Server)"]
    end
    
    subgraph "Client Types"
        CD["Claude Desktop"]
        Cursor["Cursor"]
        Web["Web Clients"]
    end
    
    CD -->|Uses| STDIO
    Cursor -->|Can use either| STDIO & SSE
    Web -->|Uses| SSE
```

Sources: [README.md:177-197](), [README.md:205-217]()

## Deployment Options

DBHub can be deployed using various methods:

### Docker Deployment

```
docker run --rm --init \
   --name dbhub \
   --publish 8080:8080 \
   bytebase/dbhub \
   --transport sse \
   --port 8080 \
   --dsn "postgres://user:password@host.docker.internal:5432/dbname?sslmode=disable"
```

### NPM Package

```
npx @bytebase/dbhub --transport sse --port 8080 --dsn "postgres://user:password@localhost:5432/dbname?sslmode=disable"
```

### Demo Mode

```
npx @bytebase/dbhub --transport sse --port 8080 --demo
```

Sources: [README.md:62-98](), [package.json:1-15]()

## Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--demo` | Run with sample employee database | `false` |
| `--dsn` | Database connection string | Required if not in demo mode |
| `--transport` | Transport mode (`stdio` or `sse`) | `stdio` |
| `--port` | HTTP server port (for SSE transport) | `8080` |

Sources: [README.md:219-226]()

## Integration with MCP Clients

DBHub integrates with various MCP clients, particularly:

### Claude Desktop

```json
// claude_desktop_config.json example
{
  "mcpServers": {
    "dbhub-postgres": {
      "command": "npx",
      "args": [
        "-y",
        "@bytebase/dbhub",
        "--transport",
        "stdio",
        "--dsn",
        "postgres://user:password@localhost:5432/dbname?sslmode=disable"
      ]
    },
    "dbhub-demo": {
      "command": "npx",
      "args": ["-y", "@bytebase/dbhub", "--transport", "stdio", "--demo"]
    }
  }
}
```

### Cursor

Cursor supports both STDIO and SSE transport modes. For SSE integration, connect to the `/sse` endpoint of the running DBHub server.

Sources: [README.md:102-151]()

## Conclusion

DBHub provides a powerful and flexible universal database gateway that implements the Model Context Protocol. It enables AI assistants and other MCP-compatible clients to interact with various database systems through a consistent interface, supporting exploration of database schema, execution of queries, and AI-assisted SQL generation.

For more detailed information, see:
- [Installation and Quick Start](#1.1) for setup instructions
- [Architecture Overview](#1.2) for deeper architectural insights
- [Core Components](#2) for implementation details
- [Database Connectors](#3) for database-specific functionality
