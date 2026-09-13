# Overview

<details>
<summary>Relevant source files</summary>

The following files were used as context for generating this wiki page:

- [.gitignore](.gitignore)
- [CHANGELOG.md](CHANGELOG.md)
- [README.md](README.md)
- [package-lock.json](package-lock.json)
- [package.json](package.json)

</details>



PeerJS is a JavaScript library that provides a complete, configurable, and easy-to-use peer-to-peer API built on top of WebRTC. It abstracts away the complexity of WebRTC implementation details, enabling developers to quickly build applications that support both data channels and media streams for real-time communication.

This document provides a high-level overview of the PeerJS library, its architecture, core components, and functionality. For installation instructions and usage examples, see [Installation and Usage](#1.1). For a complete API reference, see [API Reference](#1.2).

## Key Features

PeerJS offers several notable features that simplify WebRTC peer-to-peer communication:

- **Simplified API**: Easy-to-use interface for establishing peer connections
- **Data Channels**: Send and receive arbitrary data between peers
- **Media Streams**: Stream audio and video between peers
- **Multiple Serialization Options**: Support for different data serialization formats
- **Connection Management**: Automatic handling of connection establishment and maintenance
- **Signaling**: Built-in signaling through a PeerServer to facilitate peer discovery

Sources: [README.md:7-7](), [package.json:10-10]()

## System Architecture

The following diagram illustrates the high-level architecture of PeerJS:

```mermaid
graph TD
    subgraph "Applications"
        App1["Client Application 1"]
        App2["Client Application 2"]
    end

    subgraph "PeerJS Library"
        subgraph "Core Components"
            Peer["Peer Class"]
            DataConn["DataConnection Class"]
            MediaConn["MediaConnection Class"]
            Negotiator["Negotiator Class"]
            Socket["Socket Class"]
            API["API Class"]
        end
        
        subgraph "Utilities"
            Util["Util"]
            Supports["Browser Feature Detection"]
            Logger["Logging System"]
        end
        
        subgraph "Serialization"
            BinaryPack["BinaryPack"]
            Json["JSON"]
            MsgPack["MessagePack"]
        end
    end
    
    subgraph "External Infrastructure"
        PeerServer["PeerServer"]
        WebRTC["WebRTC API"]
        STUN["STUN Servers"]
        TURN["TURN Servers"]
    end
    
    App1 --> Peer
    App2 --> Peer
    Peer --> DataConn
    Peer --> MediaConn
    DataConn --> Negotiator
    MediaConn --> Negotiator
    Peer --> Socket
    Peer --> API
    DataConn --> BinaryPack & Json & MsgPack
    Negotiator --> WebRTC
    WebRTC --> STUN & TURN
    Socket --> PeerServer
    API --> PeerServer
```

The architecture follows a layered approach where:

1. **Applications** use the PeerJS library to establish peer-to-peer connections
2. **Core Components** handle connection management, data transmission, and media streaming
3. **External Infrastructure** provides the necessary signaling and network traversal capabilities

Sources: [README.md:7-13](), [package.json:206-211]()

## Core Components

### Peer Class

The `Peer` class is the primary entry point to the library. It manages peer identity, creates and maintains connections to other peers, and handles events for incoming connections.

### Connection Classes

PeerJS offers two types of connections:

1. **DataConnection**: Handles peer-to-peer data transfer using WebRTC data channels
2. **MediaConnection**: Manages audio/video streaming between peers

Both connection types inherit from a common base class and use the Negotiator for WebRTC connection setup.

### Negotiator

The `Negotiator` class handles WebRTC connection establishment, including SDP offer/answer exchange and ICE candidate processing.

### Socket and API

The `Socket` class maintains a WebSocket connection to the PeerServer for signaling, while the `API` class provides HTTP API functionality for peer registration and discovery.

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
        +disconnect()
        +reconnect()
        +destroy()
    }
    
    class BaseConnection {
        +peer: string
        +connectionId: string
        +open: boolean
        +metadata: any
        +type: string
        +close()
        +handleMessage(message)
    }
    
    class DataConnection {
        +serialization: string
        +reliable: boolean
        +send(data)
    }
    
    class MediaConnection {
        +localStream: MediaStream
        +remoteStream: MediaStream
        +answer(stream, options)
        +addStream(stream)
    }
    
    class Negotiator {
        +startConnection(options)
        +handleSDP(type, sdp)
        +handleCandidate(ice)
        +cleanup()
    }
    
    EventEmitter <|-- Peer
    EventEmitter <|-- BaseConnection
    BaseConnection <|-- DataConnection
    BaseConnection <|-- MediaConnection
    Peer "1" *-- "many" BaseConnection
    BaseConnection -- Negotiator
```

Sources: [README.md:40-73](), [README.md:80-112]()

## Connection Flow

The following sequence diagram illustrates how peers establish a connection:

```mermaid
sequenceDiagram
    participant PeerA as "Peer (Client A)"
    participant Server as "PeerServer"
    participant PeerB as "Peer (Client B)"
    
    PeerA->>Server: Connect (register with ID)
    Server-->>PeerA: ID Confirmed
    PeerB->>Server: Connect (register with ID)
    Server-->>PeerB: ID Confirmed
    
    PeerA->>Server: Request connection to PeerB
    Server->>PeerB: Forward connection request
    
    Note over PeerB: User accepts connection
    
    PeerB->>Server: Send answer (SDP)
    Server->>PeerA: Forward answer
    
    Note over PeerA,PeerB: WebRTC Negotiation (ICE candidates)
    
    PeerA-->>PeerB: Direct P2P connection established
    
    Note over PeerA,PeerB: Data/Media flows directly between peers
```

1. Both peers connect to the PeerServer and register with unique IDs
2. Peer A initiates a connection request to Peer B through the PeerServer
3. The PeerServer forwards the request to Peer B
4. Peer B accepts the connection and sends an answer back
5. After WebRTC negotiation completes, a direct P2P connection is established
6. Data and media flow directly between the peers without going through the server

Sources: [README.md:52-73](), [README.md:80-112]()

## Data Communication

### Data Serialization

PeerJS supports multiple serialization formats for efficient data transfer:

| Serialization | Description | Best For |
|---------------|-------------|----------|
| BinaryPack (default) | Binary format that supports complex JavaScript objects | General purpose data transfer |
| JSON | Text-based format for simple data structures | Debugging and human-readable data |
| MessagePack | Compact binary format | Performance-critical applications |

The data serialization process works as follows:

```mermaid
graph TD
    subgraph "Sending Peer"
        App1["Application"] -->|"send(data)"| DataConn1["DataConnection"]
        DataConn1 -->|"serialize"| Serializer1["Serializer (BinaryPack/JSON/MsgPack)"]
        Serializer1 -->|"chunk if needed"| RTCChannel1["RTCDataChannel"]
    end
    
    subgraph "Receiving Peer"
        RTCChannel2["RTCDataChannel"] -->|"receive chunks"| Serializer2["Serializer (BinaryPack/JSON/MsgPack)"]
        Serializer2 -->|"deserialize"| DataConn2["DataConnection"]
        DataConn2 -->|"emit 'data' event"| App2["Application"]
    end
    
    RTCChannel1 ==>|"WebRTC Direct Connection"| RTCChannel2
```

When sending data:
1. The application calls `send()` on a DataConnection
2. The data is serialized using the configured format
3. Large data is chunked if necessary
4. The data is sent through the RTCDataChannel
5. The receiving peer reassembles chunks and deserializes the data
6. A 'data' event is emitted with the received data

Sources: [package.json:206-211](), [README.md:51-69]()

## Media Streaming

PeerJS simplifies WebRTC media streaming with a straightforward API:

### Call Flow

```mermaid
sequenceDiagram
    participant Caller as "Peer 1 (Caller)"
    participant Negotiator1 as "Negotiator (Peer 1)"
    participant Server as "PeerServer"
    participant Negotiator2 as "Negotiator (Peer 2)"
    participant Callee as "Peer 2 (Callee)"
    
    Caller->>Caller: Get local media stream
    Caller->>Negotiator1: call(peerId, stream)
    Negotiator1->>Negotiator1: Create RTCPeerConnection
    Negotiator1->>Negotiator1: Add local stream
    Negotiator1->>Negotiator1: Create SDP offer
    Negotiator1->>Server: Send offer message
    Server->>Callee: Forward offer message
    
    Callee->>Callee: Get local media stream
    Callee->>Negotiator2: answer(stream)
    Negotiator2->>Negotiator2: Create RTCPeerConnection
    Negotiator2->>Negotiator2: Set remote description (offer)
    Negotiator2->>Negotiator2: Add local stream
    Negotiator2->>Negotiator2: Create SDP answer
    Negotiator2->>Server: Send answer message
    Server->>Caller: Forward answer message
    Caller->>Negotiator1: Set remote description (answer)
    
    Note over Negotiator1,Negotiator2: ICE candidate exchange
    
    Caller->>Callee: Media streams flowing directly
```

This process establishes a direct media connection between peers, allowing for real-time audio and video communication.

Sources: [README.md:80-112]()

## Browser Support

PeerJS supports modern browsers with WebRTC capabilities:

| Browser | Minimum Version |
|---------|----------------|
| Chrome  | 83+            |
| Edge    | 83+            |
| Firefox | 80+            |
| Safari  | 15+            |

Note: Firefox 102+ is required for MessagePack serialization support.

Sources: [README.md:120-132](), [package.json:138-160]()

## Integration with PeerServer

PeerJS relies on a signaling server called PeerServer to facilitate peer discovery and connection establishment. PeerServer can be:

1. The default public server at `0.peerjs.com`
2. A self-hosted instance of [PeerServer](https://github.com/peers/peerjs-server)
3. A customized server implementation that follows the PeerJS protocol

Once a connection is established via the signaling server, peers communicate directly without server intermediation.

Sources: [README.md:143-143]()

## Summary

PeerJS provides a robust abstraction over WebRTC, simplifying the development of real-time peer-to-peer applications. By handling the complexities of WebRTC negotiation, connection management, and data serialization, PeerJS enables developers to focus on building their applications rather than dealing with the intricacies of the underlying technology.

For more detailed information about specific aspects of the library, please refer to the other sections of this documentation:

- For detailed installation and usage examples, see [Installation and Usage](#1.1)
- For a complete reference of the API, see [API Reference](#1.2)
- For in-depth architecture explanation, see [Architecture](#2)
- For detailed information about core components, see [Core Components](#2.1)
