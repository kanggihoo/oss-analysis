# Server Features

<details>
<summary>Relevant source files</summary>

The following files were used as context for generating this wiki page:

- [README.md](README.md)
- [src/resources/index.ts](src/resources/index.ts)
- [src/tools/index.ts](src/tools/index.ts)

</details>



This document provides a comprehensive overview of the features and capabilities exposed by the DBHub MCP server. It covers the various resource endpoints, tools, and prompt capabilities that enable clients to interact with databases through the Model Context Protocol (MCP). For information about the specific database connector implementations, see [Database Connectors](#3).

DBHub exposes a consistent interface across multiple database types, allowing MCP clients to explore database structures and execute queries without needing to understand the specifics of each database system.

## Feature Overview

DBHub's server features can be categorized into three main groups:

1. **Resource Endpoints**: Provide structured access to database objects (schemas, tables, etc.)
2. **Tools**: Enable dynamic operations like executing queries
3. **Prompt Capabilities**: Support AI-powered features like SQL generation and database explanation

```mermaid
graph TD
    Client["MCP Client"]
    
    subgraph "DBHub Server Features"
        Resources["Resource Endpoints"]
        Tools["Tool Capabilities"]
        Prompts["Prompt Capabilities"]
    end
    
    subgraph "Resource Endpoints"
        Schemas["db://schemas"]
        Tables["db://schemas/{schema}/tables"]
        TableStructure["db://schemas/{schema}/tables/{table}"]
        Indexes["db://schemas/{schema}/tables/{table}/indexes"]
        Procedures["db://schemas/{schema}/procedures"]
        ProcDetail["db://schemas/{schema}/procedures/{procedure}"]
    end
    
    subgraph "Tool Capabilities"
        RunQuery["run_query"]
        ListConnectors["list_connectors"]
    end
    
    subgraph "Prompt Capabilities"
        GenerateSQL["generate_sql"]
        ExplainDB["explain_db"]
    end
    
    Client --> Resources
    Client --> Tools
    Client --> Prompts
    
    Resources --> Schemas
    Resources --> Tables
    Resources --> TableStructure
    Resources --> Indexes
    Resources --> Procedures
    Resources --> ProcDetail
    
    Tools --> RunQuery
    Tools --> ListConnectors
    
    Prompts --> GenerateSQL
    Prompts --> ExplainDB
```

Sources: [README.md:35-60](), [src/resources/index.ts:1-60](), [src/tools/index.ts:1-24]()

## Resource Endpoints

DBHub exposes database structures through a RESTful resource hierarchy, allowing clients to navigate and explore database objects in a structured way. Each resource endpoint maps to a specific handler that retrieves the appropriate information from the active database connector.

### Resource Hierarchy

Resources are organized in a hierarchical structure following RESTful patterns:

```mermaid
graph TD
    Root["db://"] --> Schemas["schemas"]
    Schemas --> SchemaName["{schemaName}"]
    
    SchemaName --> Tables["tables"]
    SchemaName --> Procedures["procedures"]
    
    Tables --> TableName["{tableName}"]
    Procedures --> ProcedureName["{procedureName}"]
    
    TableName --> TableStructure["table structure"]
    TableName --> Indexes["indexes"]
```

Sources: [src/resources/index.ts:18-60]()

### Resource Implementation

Resource handlers are registered with the MCP server during initialization. Each resource has a unique identifier, a URI template, and a handler function that processes requests.

```mermaid
classDiagram
    class McpServer {
        +resource(name, template, handler)
    }
    
    class ResourceHandler {
        <<interface>>
        +get(params, context): Promise~any~
    }
    
    class ResourceTemplate {
        +template: string
        +options: object
    }
    
    class registerResources {
        +function(server: McpServer): void
    }
    
    McpServer --> ResourceHandler: registers
    McpServer --> ResourceTemplate: uses
    registerResources --> McpServer: configures
    
    class schemasResourceHandler {
        implements ResourceHandler
    }
    
    class tablesResourceHandler {
        implements ResourceHandler
    }
    
    class tableStructureResourceHandler {
        implements ResourceHandler
    }
    
    class indexesResourceHandler {
        implements ResourceHandler
    }
    
    class proceduresResourceHandler {
        implements ResourceHandler
    }
    
    class procedureDetailResourceHandler {
        implements ResourceHandler
    }
    
    registerResources --> schemasResourceHandler: registers
    registerResources --> tablesResourceHandler: registers
    registerResources --> tableStructureResourceHandler: registers
    registerResources --> indexesResourceHandler: registers
    registerResources --> proceduresResourceHandler: registers
    registerResources --> procedureDetailResourceHandler: registers
```

Sources: [src/resources/index.ts:1-60]()

### Resource Compatibility Matrix

The following table shows the compatibility of each resource endpoint with different database systems:

| Resource Endpoint | URI Format | PostgreSQL | MySQL | MariaDB | SQL Server | SQLite |
|-------------------|------------|:----------:|:-----:|:-------:|:----------:|:------:|
| schemas | `db://schemas` | ✅ | ✅ | ✅ | ✅ | ✅ |
| tables_in_schema | `db://schemas/{schemaName}/tables` | ✅ | ✅ | ✅ | ✅ | ✅ |
| table_structure_in_schema | `db://schemas/{schemaName}/tables/{tableName}` | ✅ | ✅ | ✅ | ✅ | ✅ |
| indexes_in_table | `db://schemas/{schemaName}/tables/{tableName}/indexes` | ✅ | ✅ | ✅ | ✅ | ✅ |
| procedures_in_schema | `db://schemas/{schemaName}/procedures` | ✅ | ✅ | ✅ | ✅ | ❌ |
| procedure_details_in_schema | `db://schemas/{schemaName}/procedures/{procedureName}` | ✅ | ✅ | ✅ | ✅ | ❌ |

Sources: [README.md:37-47]()

## Tool Features

Tools provide dynamic functionality that allows clients to perform operations on databases. Unlike resources, which represent static database structures, tools enable actions like executing queries.

### Available Tools

DBHub provides two primary tools:

1. **run_query**: Executes SQL queries on the connected database
2. **list_connectors**: Lists available database connectors

```mermaid
sequenceDiagram
    participant Client as MCP Client
    participant Server as DBHub Server
    participant ToolHandler as Tool Handler
    participant Connector as Database Connector
    participant Database as Database

    Client->>Server: Call tool (run_query)
    Server->>ToolHandler: Route to runQueryToolHandler
    ToolHandler->>Connector: Get active connector
    ToolHandler->>Connector: validateQuery(query)
    
    alt Valid query
        Connector->>Database: Execute query
        Database->>Connector: Return results
        Connector->>ToolHandler: Return results
        ToolHandler->>Server: Return success response
    else Invalid query
        Connector->>ToolHandler: Return validation error
        ToolHandler->>Server: Return error response
    end
    
    Server->>Client: Return tool response
```

Sources: [src/tools/index.ts:1-24](), [README.md:48-53]()

### Tool Registration

Tools are registered with the MCP server during initialization:

```mermaid
classDiagram
    class McpServer {
        +tool(name, description, schema, handler)
    }
    
    class ToolHandler {
        <<interface>>
        +handle(params, context): Promise~any~
    }
    
    class registerTools {
        +function(server: McpServer): void
    }
    
    McpServer --> ToolHandler: registers
    registerTools --> McpServer: configures
    
    class runQueryToolHandler {
        implements ToolHandler
    }
    
    class listConnectorsToolHandler {
        implements ToolHandler
    }
    
    registerTools --> runQueryToolHandler: registers "run_query"
    registerTools --> listConnectorsToolHandler: registers "list_connectors"
```

Sources: [src/tools/index.ts:1-24]()

### Tool Compatibility Matrix

The following table shows the compatibility of each tool with different database systems:

| Tool | Command Name | PostgreSQL | MySQL | MariaDB | SQL Server | SQLite |
|------|--------------|:----------:|:-----:|:-------:|:----------:|:------:|
| Execute Query | `run_query` | ✅ | ✅ | ✅ | ✅ | ✅ |
| List Connectors | `list_connectors` | ✅ | ✅ | ✅ | ✅ | ✅ |

Sources: [README.md:48-53]()

## Prompt Capabilities

Prompt capabilities enable AI-powered features that enhance database interactions. These capabilities are designed to help users generate SQL queries and understand database structures through natural language.

### Available Prompt Capabilities

DBHub provides two primary prompt capabilities:

1. **generate_sql**: Generates SQL queries based on natural language descriptions
2. **explain_db**: Provides explanations of database elements and structures

### Prompt Capability Compatibility Matrix

The following table shows the compatibility of each prompt capability with different database systems:

| Prompt | Command Name | PostgreSQL | MySQL | MariaDB | SQL Server | SQLite |
|--------|--------------|:----------:|:-----:|:-------:|:----------:|:------:|
| Generate SQL | `generate_sql` | ✅ | ✅ | ✅ | ✅ | ✅ |
| Explain DB Elements | `explain_db` | ✅ | ✅ | ✅ | ✅ | ✅ |

Sources: [README.md:55-60]()

## Feature Request Flow

The following diagram illustrates how client requests flow through the DBHub server:

```mermaid
flowchart TD
    Client["MCP Client"]
    
    subgraph "DBHub Server"
        Server["MCP Server"]
        
        subgraph "Request Handlers"
            ResourceHandlers["Resource Handlers"]
            ToolHandlers["Tool Handlers"]
            PromptHandlers["Prompt Handlers"]
        end
        
        subgraph "Connector System"
            ConnectorManager["ConnectorManager"]
            Connector["Active Connector"]
        end
    end
    
    Database[(Database)]
    
    Client -->|"Request"| Server
    Server -->|"Route Request"| ResourceHandlers
    Server -->|"Route Request"| ToolHandlers
    Server -->|"Route Request"| PromptHandlers
    
    ResourceHandlers -->|"Get Connector"| ConnectorManager
    ToolHandlers -->|"Get Connector"| ConnectorManager
    PromptHandlers -->|"Get Connector"| ConnectorManager
    
    ConnectorManager -->|"Use"| Connector
    Connector -->|"Execute"| Database
    
    Database -->|"Results"| Connector
    Connector -->|"Results"| ResourceHandlers
    Connector -->|"Results"| ToolHandlers
    Connector -->|"Results"| PromptHandlers
    
    ResourceHandlers -->|"Response"| Server
    ToolHandlers -->|"Response"| Server
    PromptHandlers -->|"Response"| Server
    
    Server -->|"Response"| Client
```

Sources: [README.md:9-27](), [src/resources/index.ts:1-60](), [src/tools/index.ts:1-24]()

## Summary

DBHub's server features provide a comprehensive set of capabilities for interacting with databases through the Model Context Protocol. By exposing resources, tools, and prompt capabilities, DBHub enables MCP clients to explore database structures, execute queries, and leverage AI-powered features across multiple database systems.

The consistent interface across different database types allows users to interact with databases in a unified way, regardless of the underlying database system. This compatibility matrix ensures that users can rely on a consistent experience across supported databases, with clear indications of which features are available for each database type.
