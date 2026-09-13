# Database Connectors

<details>
<summary>Relevant source files</summary>

The following files were used as context for generating this wiki page:

- [README.md](README.md)
- [src/connectors/interface.ts](src/connectors/interface.ts)
- [src/connectors/manager.ts](src/connectors/manager.ts)

</details>



This page provides an overview of the database connector system in DBHub, which enables the universal database gateway functionality. The connector system is the abstraction layer that allows DBHub to communicate with multiple database types through a consistent interface.

For information about the overall connector architecture and management, see [Connector System](#2.2). For details about specific database connector implementations, refer to: [SQL Server Connector](#3.1), [MySQL and MariaDB Connectors](#3.2), [PostgreSQL Connector](#3.3), and [SQLite Connector](#3.4).

## Connector System Overview

The database connector system is a core component of DBHub that enables communication with different types of databases through a standardized interface. Each connector implements database-specific functionality while exposing a consistent API to the rest of the application.

```mermaid
flowchart TD
    subgraph "DBHub Core"
        Server["MCP Server"]
        Resources["Resources Handler"]
        Tools["Tools Handler"]
    end
    
    subgraph "Connector System"
        CM["ConnectorManager"]
        CR["ConnectorRegistry"]
        
        subgraph "Connector Interface"
            CI["Connector Interface"]
            DP["DSNParser Interface"]
        end
        
        subgraph "Database Connectors"
            PG["PostgresConnector"]
            MSSQL["SQLServerConnector"]
            MySQL["MySQLConnector"]
            MariaDB["MariaDBConnector"]
            SQLite["SQLiteConnector"]
        end
    end
    
    subgraph "Databases"
        PostgreSQL[(PostgreSQL)]
        SQLServer[(SQL Server)]
        MySQLDB[(MySQL)]
        MariaDBDB[(MariaDB)]
        SQLiteDB[(SQLite)]
    end
    
    Server --> Resources & Tools
    Resources & Tools --> CM
    CM --> CR
    CR --> PG & MSSQL & MySQL & MariaDB & SQLite
    
    CI --> PG & MSSQL & MySQL & MariaDB & SQLite
    DP --> PG & MSSQL & MySQL & MariaDB & SQLite
    
    PG --> PostgreSQL
    MSSQL --> SQLServer
    MySQL --> MySQLDB
    MariaDB --> MariaDBDB
    SQLite --> SQLiteDB
```

Sources: [src/connectors/interface.ts:5-139](), [src/connectors/manager.ts:9-109]()

## Supported Database Systems

DBHub currently supports the following database systems:

| Database   | Connector ID | Connection String Format                                | Sample DSN                                               |
|------------|--------------|--------------------------------------------------------|----------------------------------------------------------|
| PostgreSQL | postgres     | `postgres://[user]:[password]@[host]:[port]/[database]` | `postgres://user:password@localhost:5432/dbname?sslmode=disable` |
| MySQL      | mysql        | `mysql://[user]:[password]@[host]:[port]/[database]`    | `mysql://user:password@localhost:3306/dbname`            |
| MariaDB    | mariadb      | `mariadb://[user]:[password]@[host]:[port]/[database]`  | `mariadb://user:password@localhost:3306/dbname`          |
| SQL Server | sqlserver    | `sqlserver://[user]:[password]@[host]:[port]/[database]`| `sqlserver://user:password@localhost:1433/dbname`        |
| SQLite     | sqlite       | `sqlite:///[path/to/file]` or `sqlite::memory:`         | `sqlite:///path/to/database.db` or `sqlite::memory:`     |

Sources: [README.md:189-196]()

## Connector Interface Architecture

The connector system is designed around a core interface that all database connectors must implement. This design ensures that the MCP server can interact with different database types in a consistent manner.

```mermaid
classDiagram
    class Connector {
        <<interface>>
        +id: string
        +name: string
        +dsnParser: DSNParser
        +connect(dsn: string, initScript?: string): Promise~void~
        +disconnect(): Promise~void~
        +getSchemas(): Promise~string[]~
        +getTables(schema?: string): Promise~string[]~
        +tableExists(tableName: string, schema?: string): Promise~boolean~
        +getTableSchema(tableName: string, schema?: string): Promise~TableColumn[]~
        +getTableIndexes(tableName: string, schema?: string): Promise~TableIndex[]~
        +getStoredProcedures(schema?: string): Promise~string[]~
        +getStoredProcedureDetail(procedureName: string, schema?: string): Promise~StoredProcedure~
        +executeQuery(query: string): Promise~QueryResult~
        +validateQuery(query: string): {isValid: boolean; message?: string}
    }
    
    class DSNParser {
        <<interface>>
        +parse(dsn: string): Promise~any~
        +getSampleDSN(): string
        +isValidDSN(dsn: string): boolean
    }
    
    class ConnectorRegistry {
        -static connectors: Map~string, Connector~
        +static register(connector: Connector): void
        +static getConnector(id: string): Connector | null
        +static getConnectorForDSN(dsn: string): Connector | null
        +static getAvailableConnectors(): string[]
        +static getSampleDSN(connectorId: string): string | null
    }
    
    class ConnectorManager {
        -activeConnector: Connector | null
        -connected: boolean
        +connectWithDSN(dsn: string, initScript?: string): Promise~void~
        +disconnect(): Promise~void~
        +getConnector(): Connector
        +isConnected(): boolean
        +static getCurrentConnector(): Connector
    }
    
    Connector --> DSNParser: contains
    ConnectorRegistry o-- Connector: registers
    ConnectorManager --> Connector: manages active
    ConnectorManager --> ConnectorRegistry: uses
```

Sources: [src/connectors/interface.ts:37-139](), [src/connectors/manager.ts:9-109]()

## Core Connector Components

### Connector Interface

All database connectors implement the `Connector` interface, which defines the contract that each connector must fulfill. The interface includes methods for:

1. Connecting and disconnecting from a database
2. Retrieving database metadata (schemas, tables, columns, indexes)
3. Accessing stored procedures (for supported databases)
4. Executing and validating queries

The key methods in the `Connector` interface are:

| Method | Purpose |
|--------|---------|
| `connect(dsn: string, initScript?: string)` | Establishes a database connection using the provided DSN |
| `disconnect()` | Closes the database connection |
| `getSchemas()` | Retrieves all schemas in the database |
| `getTables(schema?: string)` | Gets all tables in a specific schema or default schema |
| `getTableSchema(tableName: string, schema?: string)` | Retrieves column information for a table |
| `getTableIndexes(tableName: string, schema?: string)` | Gets indexes for a specific table |
| `executeQuery(query: string)` | Executes an SQL query and returns the results |
| `validateQuery(query: string)` | Validates a query for safety before execution |

Sources: [src/connectors/interface.ts:59-139]()

### Data Structures

The connector system defines several common data structures for representing database objects:

```mermaid
classDiagram
    class TableColumn {
        +column_name: string
        +data_type: string
        +is_nullable: string
        +column_default: string | null
    }
    
    class TableIndex {
        +index_name: string
        +column_names: string[]
        +is_unique: boolean
        +is_primary: boolean
    }
    
    class StoredProcedure {
        +procedure_name: string
        +procedure_type: "procedure" | "function"
        +language: string
        +parameter_list: string
        +return_type?: string
        +definition?: string
    }
    
    class QueryResult {
        +rows: any[]
        +[key: string]: any
    }
```

Sources: [src/connectors/interface.ts:5-31]()

### DSN Parsers

Each database connector includes a DSN (Database Source Name) parser that understands the specific connection string format for that database type. The parsers implement the `DSNParser` interface, which includes methods for:

1. Parsing a connection string into database-specific configuration
2. Providing sample DSN strings
3. Validating DSN formats

Sources: [src/connectors/interface.ts:37-57]()

## Connection Management

The `ConnectorManager` is responsible for managing the active database connection. It provides a singleton instance that can be accessed globally throughout the application, making it easy for MCP resources and tools to interact with the current database.

```mermaid
sequenceDiagram
    participant Server as MCP Server
    participant Manager as ConnectorManager
    participant Registry as ConnectorRegistry
    participant Connector as Database Connector
    participant DB as Database
    
    Server->>Manager: connectWithDSN(dsn)
    Manager->>Registry: getConnectorForDSN(dsn)
    Registry->>Registry: Find matching connector
    Registry-->>Manager: Return connector instance
    
    Manager->>Manager: Set activeConnector
    Manager->>Connector: connect(dsn)
    Connector->>Connector: Parse DSN
    Connector->>DB: Establish connection
    DB-->>Connector: Connection established
    Connector-->>Manager: Connection success
    
    Note over Manager: Connection active
    
    Server->>Manager: getCurrentConnector()
    Manager-->>Server: Active connector instance
    
    Server->>Connector: executeQuery(query)
    Connector->>DB: Execute query
    DB-->>Connector: Query results
    Connector-->>Server: Return results
    
    Server->>Manager: disconnect()
    Manager->>Connector: disconnect()
    Connector->>DB: Close connection
    DB-->>Connector: Connection closed
    Connector-->>Manager: Disconnection success
```

Sources: [src/connectors/manager.ts:9-109]()

## Connector Registry

The `ConnectorRegistry` class provides a central registry for all available database connectors. It uses a static map to store connector instances, indexed by their unique identifiers. The registry has methods for:

1. Registering new connectors
2. Retrieving connectors by ID or DSN format
3. Listing available connectors
4. Providing sample DSN strings

This registry pattern allows for dynamic discovery of available connectors and enables the system to select the appropriate connector based on the provided DSN.

Sources: [src/connectors/interface.ts:144-200]()

## Feature Compatibility Matrix

Not all database connectors support the same features. The table below shows the compatibility matrix for various database resources and operations:

| Resource | PostgreSQL | MySQL | MariaDB | SQL Server | SQLite |
|----------|:----------:|:-----:|:-------:|:----------:|:------:|
| Schemas | ✅ | ✅ | ✅ | ✅ | ✅ |
| Tables | ✅ | ✅ | ✅ | ✅ | ✅ |
| Table Structure | ✅ | ✅ | ✅ | ✅ | ✅ |
| Indexes | ✅ | ✅ | ✅ | ✅ | ✅ |
| Stored Procedures | ✅ | ✅ | ✅ | ✅ | ❌ |
| Query Execution | ✅ | ✅ | ✅ | ✅ | ✅ |

Sources: [README.md:37-47](), [README.md:50-53]()

## Connection Workflow

When an MCP client connects to DBHub, the following sequence occurs to establish a database connection:

1. The client provides a DSN (either directly or through configuration)
2. The `ConnectorRegistry` identifies the appropriate connector for the DSN format
3. The `ConnectorManager` activates the connector and establishes a connection
4. Once connected, MCP resources and tools can access database functionality through the active connector

This abstraction allows MCP clients to interact with different database types without needing to understand the specifics of each database's connection mechanisms.

Sources: [src/connectors/manager.ts:22-36]()
