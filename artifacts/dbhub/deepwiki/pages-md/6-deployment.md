# Deployment

<details>
<summary>Relevant source files</summary>

The following files were used as context for generating this wiki page:

- [.dockerignore](.dockerignore)
- [.github/workflows/docker-publish.yml](.github/workflows/docker-publish.yml)
- [.github/workflows/npm-publish.yml](.github/workflows/npm-publish.yml)
- [Dockerfile](Dockerfile)
- [README.md](README.md)
- [package.json](package.json)

</details>



This page provides a comprehensive overview of deployment options for DBHub, a universal database gateway implementing the Model Context Protocol (MCP) server interface. It covers both Docker container and NPM package deployment methods, with detailed instructions and configuration options for each. For specific details about Docker deployment, see [Docker Deployment](#6.1). For information about NPM packaging, see [NPM Packaging](#6.2).

## Deployment Options Overview

DBHub can be deployed using two primary methods, each with different use cases and configuration approaches:

```mermaid
flowchart TD
    Root["DBHub Deployment Options"]
    Docker["Docker Container\nbytebase/dbhub"]
    NPM["NPM Package\n@bytebase/dbhub"]
    
    Root --> Docker
    Root --> NPM
    
    DockerCLI["Command Line\ndocker run --rm bytebase/dbhub"]
    DockerCompose["Docker Compose\nservices:\n  dbhub:\n    image: bytebase/dbhub"]
    
    Docker --> DockerCLI
    Docker --> DockerCompose
    
    NPMGlobal["Global Installation\nnpm install -g @bytebase/dbhub"]
    NPXCLI["Direct Execution\nnpx @bytebase/dbhub"]
    ClaudeConfig["Claude Desktop Integration\nclause_desktop_config.json"]
    
    NPM --> NPMGlobal
    NPM --> NPXCLI
    NPM --> ClaudeConfig
```

Sources: [README.md:62-87](), [README.md:88-100](), [README.md:102-143]()

## Docker Deployment

### Docker Image

The official Docker image is available at `bytebase/dbhub` on Docker Hub. It supports both AMD64 (x86_64) and ARM64 architectures. The image is built using a multi-stage Dockerfile that:

1. Uses Node.js 22 Alpine as the base image
2. Installs dependencies using pnpm
3. Builds the TypeScript code
4. Creates a minimal production image with only necessary dependencies

Sources: [Dockerfile:1-43]()

### Running with Docker

To run DBHub using Docker with a database connection:

```bash
docker run --rm --init \
   --name dbhub \
   --publish 8080:8080 \
   bytebase/dbhub \
   --transport sse \
   --port 8080 \
   --dsn "postgres://user:password@host.docker.internal:5432/dbname?sslmode=disable"
```

For demo mode with the sample employee database:

```bash
docker run --rm --init \
   --name dbhub \
   --publish 8080:8080 \
   bytebase/dbhub \
   --transport sse \
   --port 8080 \
   --demo
```

Sources: [README.md:64-86]()

### Docker Build and Publish Workflow

The Docker image is built and published automatically using GitHub Actions:

```mermaid
flowchart TD
    SourceCode["Source Code\nGitHub Repository"]
    Dockerfile["Dockerfile\nMulti-stage Build Process"]
    GitHubAction["docker-publish.yml\nGitHub Actions Workflow"]
    DockerRegistry["Docker Hub Registry\nbytebase/dbhub"]
    
    SourceCode --> Dockerfile
    SourceCode --> GitHubAction
    Dockerfile --> GitHubAction
    GitHubAction --> DockerRegistry
    
    LatestTag["latest tag\nAlways updated on main branch"]
    VersionTag["version tag\nWhen package.json version changes"]
    
    DockerRegistry --> LatestTag
    DockerRegistry --> VersionTag
    
    DeployCmd["docker run Command\nwith Configuration Options"]
    
    LatestTag --> DeployCmd
    VersionTag --> DeployCmd
```

Sources: [.github/workflows/docker-publish.yml:1-86](), [Dockerfile:1-43]()

## NPM Deployment

### NPM Package

The NPM package is published to the registry as `@bytebase/dbhub`. The package.json configuration specifies:

- Main entry point: `dist/index.js`
- Binary entry: `dbhub` for CLI usage
- Files included in the package: `dist`, `LICENSE`, `README.md`

Sources: [package.json:1-60]()

### Installation and Usage

**Global Installation:**
```bash
npm install -g @bytebase/dbhub
dbhub --transport sse --port 8080 --dsn "postgres://user:password@localhost:5432/dbname?sslmode=disable"
```

**Direct Execution with npx:**
```bash
npx @bytebase/dbhub --transport sse --port 8080 --dsn "postgres://user:password@localhost:5432/dbname?sslmode=disable"
```

**Demo Mode:**
```bash
npx @bytebase/dbhub --transport sse --port 8080 --demo
```

Sources: [README.md:88-100]()

### NPM Build and Publish Workflow

The NPM package is built and published automatically using GitHub Actions:

```mermaid
flowchart TD
    SourceCode["Source Code\nGitHub Repository"]
    PackageJSON["package.json\nNPM Package Definition"]
    GitHubAction["npm-publish.yml\nGitHub Actions Workflow"]
    NPMRegistry["NPM Registry\n@bytebase/dbhub"]
    
    SourceCode --> PackageJSON
    SourceCode --> GitHubAction
    PackageJSON --> GitHubAction
    GitHubAction --> NPMRegistry
    
    LatestTag["latest tag\nStable versions without prerelease suffix"]
    BetaTag["beta/dev tags\nVersions with prerelease suffix"]
    
    NPMRegistry --> LatestTag
    NPMRegistry --> BetaTag
    
    NPMInstall["npm install -g @bytebase/dbhub\nor\nnpx @bytebase/dbhub"]
    
    LatestTag --> NPMInstall
    BetaTag --> NPMInstall
```

Sources: [.github/workflows/npm-publish.yml:1-155](), [package.json:1-60]()

## Integration with MCP Clients

### Claude Desktop

Claude Desktop requires the `stdio` transport. You can add DBHub to your Claude Desktop configuration:

```json
// claude_desktop_config.json
{
  "mcpServers": {
    "dbhub-postgres-docker": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "bytebase/dbhub",
        "--transport",
        "stdio",
        "--dsn",
        "postgres://user:password@host.docker.internal:5432/dbname?sslmode=disable"
      ]
    },
    "dbhub-demo": {
      "command": "npx",
      "args": ["-y", "@bytebase/dbhub", "--transport", "stdio", "--demo"]
    }
  }
}
```

Sources: [README.md:102-143]()

### Cursor

Cursor supports both `stdio` and `sse` transports. For `sse`, you can run DBHub as a server and connect to the `/sse` endpoint.

Sources: [README.md:146-151]()

## Common Configuration

### Command Line Options

Both deployment methods support the same command line options:

| Option    | Description                                                     | Default                      |
| --------- | --------------------------------------------------------------- | ---------------------------- |
| demo      | Run in demo mode with sample employee database                  | `false`                      |
| dsn       | Database connection string                                      | Required if not in demo mode |
| transport | Transport mode: `stdio` or `sse`                                | `stdio`                      |
| port      | HTTP server port (only applicable when using `--transport=sse`) | `8080`                       |

Sources: [README.md:219-226]()

### Database Connection String (DSN)

DBHub supports the following database connection formats:

| Database   | DSN Format                                               | Example                                                          |
| ---------- | -------------------------------------------------------- | ---------------------------------------------------------------- |
| MySQL      | `mysql://[user]:[password]@[host]:[port]/[database]`     | `mysql://user:password@localhost:3306/dbname`                    |
| MariaDB    | `mariadb://[user]:[password]@[host]:[port]/[database]`   | `mariadb://user:password@localhost:3306/dbname`                  |
| PostgreSQL | `postgres://[user]:[password]@[host]:[port]/[database]`  | `postgres://user:password@localhost:5432/dbname?sslmode=disable` |
| SQL Server | `sqlserver://[user]:[password]@[host]:[port]/[database]` | `sqlserver://user:password@localhost:1433/dbname`                |
| SQLite     | `sqlite:///[path/to/file]` or `sqlite::memory:`          | `sqlite:///path/to/database.db` or `sqlite::memory:`             |

You can provide the DSN in several ways (in order of priority):

1. Command line argument:
   ```bash
   --dsn "postgres://user:password@localhost:5432/dbname?sslmode=disable"
   ```

2. Environment variable:
   ```bash
   export DSN="postgres://user:password@localhost:5432/dbname?sslmode=disable"
   ```

3. Environment file:
   - For development: Create `.env.local` with your DSN
   - For production: Create `.env` with your DSN

Sources: [README.md:154-196]()

### Transport Options

DBHub supports two transport modes:

1. **stdio** (default) - for direct integration with tools like Claude Desktop:
   ```bash
   --transport stdio
   ```

2. **sse** - for browser and network clients:
   ```bash
   --transport sse --port 5678
   ```

Sources: [README.md:205-216]()

### Docker Host Configuration

When running in Docker, use `host.docker.internal` instead of `localhost` to connect to databases running on your host machine:

```bash
--dsn "mysql://user:password@host.docker.internal:3306/dbname"
```

Sources: [README.md:184-186]()

## End-to-End Deployment Flow

This diagram illustrates the complete deployment flow from source code to running instance:

```mermaid
flowchart TD
    SourceCode["Source Code\nGitHub Repository"]
    
    subgraph "Docker Deployment"
        DockerWorkflow["docker-publish.yml\nGitHub Actions Workflow"]
        DockerImage["Docker Hub\nbytebase/dbhub"]
        DockerRun["Docker Run\nwith Configuration"]
    end
    
    subgraph "NPM Deployment"
        NPMWorkflow["npm-publish.yml\nGitHub Actions Workflow"]
        NPMPackage["NPM Registry\n@bytebase/dbhub"]
        NPMRun["NPM/NPX Run\nwith Configuration"]
    end
    
    SourceCode --> DockerWorkflow
    SourceCode --> NPMWorkflow
    
    DockerWorkflow --> DockerImage
    NPMWorkflow --> NPMPackage
    
    DockerImage --> DockerRun
    NPMPackage --> NPMRun
    
    subgraph "DBHub Server"
        Transport["Transport Layer\n(STDIO or SSE)"]
        Connection["Database Connection\n(DSN or Demo Mode)"]
        Server["DBHub MCP Server"]
    end
    
    DockerRun --> Transport
    DockerRun --> Connection
    NPMRun --> Transport
    NPMRun --> Connection
    
    Transport --> Server
    Connection --> Server
    
    MCPClient["MCP Client\n(Claude Desktop, Cursor, etc.)"]
    
    Server --> MCPClient
```

Sources: [README.md:1-27](), [.github/workflows/docker-publish.yml:1-86](), [.github/workflows/npm-publish.yml:1-155]()

This diagram shows the complete flow from source code to deployment options, and how they connect to MCP clients through the DBHub server.
