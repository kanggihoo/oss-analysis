# Architecture

<details>
<summary>Relevant source files</summary>

The following files were used as context for generating this wiki page:

- [README.md](README.md)
- [lib/api.ts](lib/api.ts)
- [lib/baseconnection.ts](lib/baseconnection.ts)
- [lib/enums.ts](lib/enums.ts)
- [lib/exports.ts](lib/exports.ts)
- [lib/logger.ts](lib/logger.ts)
- [lib/optionInterfaces.ts](lib/optionInterfaces.ts)
- [lib/peer.ts](lib/peer.ts)
- [lib/servermessage.ts](lib/servermessage.ts)
- [lib/socket.ts](lib/socket.ts)
- [tsconfig.json](tsconfig.json)

</details>



This document provides an overview of the PeerJS architecture, explaining how the library is structured and how its components interact to enable WebRTC-based peer-to-peer communication. For information about individual components, see [Core Components](#2.1), and for details on how connections are established and managed, see [Connection Flow](#2.2).

## System Overview

PeerJS is designed with a hybrid architecture that uses a centralized signaling server (PeerServer) for peer discovery and initial connection establishment, followed by direct peer-to-peer communication through WebRTC. This approach simplifies the complex WebRTC API while maintaining the performance benefits of direct connections.

```mermaid
graph TD
    subgraph "Client Application"
        App["Application Code"]
    end

    subgraph "PeerJS Library"
        Peer["Peer Class"] 
        DataConn["DataConnection Classes"]
        MediaConn["MediaConnection"]
        Socket["Socket"]
        API["API"]
        Negotiator["Negotiator"]
        Serializers["Serializers (BinaryPack/Json/MsgPack)"]
        Util["Utilities"]
    end

    subgraph "External Components"
        PeerServer["PeerServer"]
        WebRTC["WebRTC API"]
        STUN["STUN Servers"]
        TURN["TURN Servers"]
    end

    App --> Peer
    Peer --> DataConn
    Peer --> MediaConn
    Peer --> Socket
    Peer --> API
    
    DataConn --> Negotiator
    MediaConn --> Negotiator
    DataConn --> Serializers
    
    Socket --> PeerServer
    API --> PeerServer
    
    Negotiator --> WebRTC
    WebRTC --> STUN
    WebRTC --> TURN
```

Sources: [lib/peer.ts:113-744](), [lib/socket.ts:10-172](), [lib/api.ts:6-85]()

## Core Components Structure

The PeerJS library consists of several interrelated components that work together to provide a simple interface for WebRTC functionality:

```mermaid
classDiagram
    class EventEmitter {
        +on(event, callback)
        +emit(event, data)
    }
    
    class Peer {
        +id: string
        +connections: Map
        +connect(peerId, options): DataConnection
        +call(peerId, stream, options): MediaConnection
        +destroy()
        +disconnect()
        +reconnect()
    }
    
    class BaseConnection {
        <<abstract>>
        +peer: string
        +connectionId: string
        +metadata: any
        +type: ConnectionType
        +close()
        +handleMessage(message)
    }
    
    class DataConnection {
        +serialization: string
        +send(data)
    }
    
    class MediaConnection {
        +localStream: MediaStream
        +answer(stream)
    }
    
    class Socket {
        +start(id, token)
        +send(data)
        +close()
    }
    
    class API {
        +retrieveId()
        +listAllPeers()
    }
    
    class Negotiator {
        +startConnection()
        +handleSDP()
        +handleCandidate()
    }
    
    EventEmitter <|-- Peer
    EventEmitter <|-- BaseConnection
    BaseConnection <|-- DataConnection
    BaseConnection <|-- MediaConnection
    Peer "1" *-- "*" BaseConnection
    BaseConnection -- Negotiator
    Peer "1" *-- "1" Socket
    Peer "1" *-- "1" API
```

Sources: [lib/peer.ts:113-144](), [lib/baseconnection.ts:32-91](), [lib/socket.ts:10-20](), [lib/api.ts:6-7]()

## Key Component Responsibilities

The PeerJS architecture separates concerns into distinct components with specific responsibilities:

| Component | Responsibility | Key Files |
|-----------|---------------|-----------|
| **Peer** | The main entry point and controller, manages peer identity and connections | [lib/peer.ts]() |
| **BaseConnection** | Abstract base class for connections, defines common functionality | [lib/baseconnection.ts]() |
| **DataConnection** | Manages data transmission between peers | [lib/dataconnection/*.ts]() |
| **MediaConnection** | Handles media streams between peers | [lib/mediaconnection.ts]() |
| **Socket** | Manages WebSocket communication with the PeerServer | [lib/socket.ts]() |
| **API** | Handles HTTP requests to the PeerServer (e.g., retrieving ID) | [lib/api.ts]() |
| **Negotiator** | Manages WebRTC connection negotiation and ICE candidate exchange | [lib/negotiator.ts]() |
| **Serializers** | Handle data serialization (BinaryPack, JSON, MsgPack) | [lib/dataconnection/BufferedConnection/*.ts]() |

Sources: [lib/exports.ts:1-27](), [lib/peer.ts:113-196](), [lib/socket.ts:6-11](), [lib/api.ts:6-7]()

## Connection Establishment Flow

The process of establishing a connection between two peers involves several steps across both the signaling server and direct WebRTC connections:

```mermaid
sequenceDiagram
    participant ClientA as "Peer A"
    participant Server as "PeerServer"
    participant ClientB as "Peer B"
    
    Note over ClientA: new Peer()
    ClientA->>Server: Connect (register ID)
    Server-->>ClientA: ID Assigned (OPEN message)
    
    Note over ClientB: new Peer()
    ClientB->>Server: Connect (register ID)
    Server-->>ClientB: ID Assigned (OPEN message)
    
    Note over ClientA: peer.connect() or peer.call()
    ClientA->>Server: OFFER message with SDP
    Server->>ClientB: Forward OFFER message
    
    Note over ClientB: Trigger "connection" or "call" event
    ClientB->>Server: ANSWER message with SDP
    Server->>ClientA: Forward ANSWER message
    
    Note over ClientA, ClientB: ICE candidate exchange via server
    ClientA->>Server: CANDIDATE messages
    Server->>ClientB: Forward CANDIDATE messages
    ClientB->>Server: CANDIDATE messages
    Server->>ClientA: Forward CANDIDATE messages
    
    Note over ClientA, ClientB: Direct P2P connection established
    ClientA-->>ClientB: Data/Media flows directly
```

Sources: [lib/peer.ts:348-458](), [lib/socket.ts:33-85](), [lib/peer.ts:484-555]()

## Data Flow and Serialization

PeerJS supports different serialization methods for data transmission, with each following a specific path from sender to receiver:

```mermaid
graph TD
    subgraph "Sending Peer"
        App1["Application"] -->|"send(data)"| DataConn1["DataConnection"]
        DataConn1 -->|"Serialize"| Serializer1["Serializer\n(BinaryPack/Json/MsgPack)"]
        Serializer1 -->|"Chunk if needed"| RTCDataChannel1["RTCDataChannel"]
    end
    
    subgraph "Receiving Peer"
        RTCDataChannel2["RTCDataChannel"] -->|"Receive data"| Serializer2["Serializer\n(BinaryPack/Json/MsgPack)"]
        Serializer2 -->|"Reassemble chunks"| DataConn2["DataConnection"]
        DataConn2 -->|"emit 'data' event"| App2["Application"]
    end
    
    RTCDataChannel1 ===|"Direct WebRTC connection"| RTCDataChannel2
```

Sources: [lib/peer.ts:116-123](), [lib/exports.ts:19-22]()

## Peer Lifecycle Management

The `Peer` class manages the lifecycle of peer connections, from creation to destruction:

```mermaid
stateDiagram-v2
    [*] --> Creating: new Peer()
    Creating --> Connecting: Constructor initialization
    Connecting --> Connected: "open" event
    Connected --> Disconnected: disconnect()
    Disconnected --> Connected: reconnect()
    Connected --> Destroyed: destroy()
    Disconnected --> Destroyed: destroy()
    Destroyed --> [*]
    
    state Connected {
        [*] --> Idle
        Idle --> CreatingConnection: connect()/call()
        CreatingConnection --> Active: Connection established
        Active --> ClosingConnection: connection.close()
        ClosingConnection --> Idle
    }
```

Sources: [lib/peer.ts:195-212](), [lib/peer.ts:640-730]()

## Error Handling Architecture

PeerJS implements a comprehensive error handling system that propagates errors through the component hierarchy:

```mermaid
graph TD
    subgraph "Error Sources"
        WebRTCErrors["WebRTC Errors"]
        ServerErrors["Server Communication Errors"]
        PeerErrors["Peer Configuration Errors"]
        ConnectionErrors["Connection Errors"]
    end
    
    subgraph "Error Handling"
        PeerErrorEmitter["Peer Error Emission"]
        ConnectionErrorEmitter["Connection Error Emission"]
    end
    
    subgraph "Application"
        ErrorHandlers["Application Error Handlers"]
    end
    
    WebRTCErrors --> ConnectionErrorEmitter
    ServerErrors --> PeerErrorEmitter
    PeerErrors --> PeerErrorEmitter
    ConnectionErrors --> ConnectionErrorEmitter
    
    ConnectionErrorEmitter --> PeerErrorEmitter
    PeerErrorEmitter --> ErrorHandlers
```

Sources: [lib/enums.ts:6-61](), [lib/enums.ts:63-71](), [lib/peer.ts:107-108]()

## Integration with External Components

PeerJS relies on several external components for its functionality:

1. **PeerServer**: A signaling server that facilitates peer discovery and connection establishment
2. **WebRTC API**: Browser's native WebRTC implementation for establishing peer-to-peer connections
3. **STUN/TURN Servers**: For NAT traversal and fallback relay if direct connection isn't possible

The library provides configuration options to customize the connection to these external components through the `Peer` constructor options:

```mermaid
graph TD
    subgraph "PeerJS Configuration"
        PeerOptions["PeerOptions"]
        RTCConfiguration["RTCConfiguration"]
        SecurityOptions["Security Options"]
        ServerOptions["Server Options"]
    end
    
    subgraph "External Services"
        CustomPeerServer["Custom PeerServer"]
        CloudPeerServer["Cloud PeerServer (0.peerjs.com)"]
        CustomSTUN["Custom STUN/TURN Servers"]
        DefaultSTUN["Default STUN/TURN Servers"]
    end
    
    PeerOptions --> RTCConfiguration
    PeerOptions --> SecurityOptions
    PeerOptions --> ServerOptions
    
    ServerOptions -->|"host, port, path"| CustomPeerServer
    ServerOptions -->|"default"| CloudPeerServer
    RTCConfiguration -->|"custom ice servers"| CustomSTUN
    RTCConfiguration -->|"default"| DefaultSTUN
```

Sources: [lib/peer.ts:25-68](), [lib/optionInterfaces.ts:8-18]()

## Summary

The PeerJS architecture employs a layered design that abstracts the complexity of WebRTC while providing a robust and flexible API for peer-to-peer communication. The library uses a hybrid approach with a central signaling server for connection establishment and direct peer-to-peer connections for data and media transfer. This design allows for efficient communication while simplifying the developer experience.

The core components (Peer, DataConnection, MediaConnection, Socket, API, and Negotiator) work together to provide a complete solution for WebRTC-based peer-to-peer applications, with support for various serialization methods and connection types.

For more detailed information about the core components and their functionalities, see [Core Components](#2.1), and for an in-depth explanation of the connection flow, see [Connection Flow](#2.2).
