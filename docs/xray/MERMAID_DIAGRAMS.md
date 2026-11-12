# Mermaid Diagrams

> ⚡ **BLUF**: Three architecture diagrams document the Nuvio launch flow,
> LCKV bridge lifecycle, and stack-item state machine. All use valid Mermaid
> syntax and are under 45 edge definitions each.

## Nuvio Deep-Link Launch Flow

```mermaid
flowchart TD
    A[User card click] --> B[Effect::NuvioLaunch]
    B --> C[validate_nuvio_target()]
    C --> D{nuvio_lab feature?}
    D -- yes --> E[appId = space.nuvio.lab]
    D -- no --> F[appId = space.nuvio.webos]
    E --> G[call("luna://com.palmdtv.applauncher/launch")]
    F --> G
    G --> H[Nuvio opens title]
```

## LCKV Bridge Lifecycle

```mermaid
stateDiagram-v2
    [*] --> ReadHeader
    ReadHeader --> ParseCards : head==tail && even
    ParseCards --> EmptyList : no cards
    ParseCards --> ReturnCards : cards present
    EmptyList --> [*]
    ReturnCards --> [*]
```

## StackItem State Machine

```mermaid
stateDiagram-v2
    [*] --> Created
    Created --> Visible : row rendered
    Visible --> Focused : focus gained
    Focused --> Hidden : focus lost
    Hidden --> [*] : row dropped
```
