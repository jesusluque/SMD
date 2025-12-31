# Self Media Decoder (SMD)

## Draft Technical Specification Version 1.1 

### Secure, Introspectable, Stateful Media with Embedded or Referenced Logic

**Status**: Draft
**Supersedes**: Version 1.0
**Change Scope**: Capability Introspection, Secure Version Lineage, Lightweight Logic Referencing, Canonicalization, Runtime Constraints

---

## 1. Abstract and Core Design Philosophy

The **Self Media Decoder (SMD)** specification defines a media format and execution model in which media assets carry or reference their own decoding logic. This represents a structural transition from the traditional *codecs-in-OS* model toward **codecs-in-media**, typically expressed as WebAssembly modules.

SMD is designed to enable:

* Stateful decoding across segmented media
* Deterministic decoder upgrades without player updates
* Secure, verifiable evolution of decoding logic
* Explicit capability introspection prior to decoding
* Lightweight media segments decoupled from decoder payloads

In SMD, media is treated as an **active, self-describing system**, not as passive encoded data.

---

## 2. SMD Atom Structure

An SMD stream consists of a temporally ordered sequence of **Atoms**.
Each Atom represents a bounded interval of media together with metadata describing decoding logic, parameters, and continuity.

Atoms are scoped to an **OriginUUID**, which defines the lifetime of decoder state and upgrade lineage.

---

## 2.1 Sequence Header (SH)

Each Atom **MUST** include a Sequence Header containing:

* **AtomUUID**: Globally unique identifier for the Atom
* **SourceUUID**: Identifier of the media source
* **OriginUUID**: Identifier defining decoder state and upgrade scope
* **AtomStartTime**: Presentation start time
* **AtomDuration**: Duration of the Atom

### Ordering Rules

* Atoms sharing an OriginUUID **MUST** be ordered by AtomStartTime.
* AtomStartTime **MUST NOT** decrease, unless a discontinuity is explicitly declared.
* Players **MAY** accept out-of-order delivery but **MUST** reorder prior to decoding.
* An optional **SequenceNumber** (uint64) **MAY** be used for deterministic ordering over unreliable transports.
* Discontinuities **SHOULD** be declared using a TimelineEpoch or DiscontinuityFlag.

---

## 2.2 Media Descriptor

The Media Descriptor declares **encoded media characteristics**, independently of decoding logic.

The descriptor:

* **MUST** be declarative
* **MUST NOT** embed executable logic
* **MUST** be canonically serializable

### Supported Media Classes (non-exhaustive)

* Image
* Video
* Volumetric or 3D
* Multi-view or stereo
* Future or unknown media types

### Canonical Encoding

* Media Descriptors **SHOULD** use CBOR Canonical Encoding (CBOR-C14N).
* Unknown fields **MUST** be preserved as opaque structured data.

---

## 2.3 Logic Identity and Versioning

### 2.3.1 Logic Identity

Decoding logic is identified by:

* **LogicVersion (LV)**
  A monotonically increasing unsigned integer scoped to OriginUUID.

* **LogicFingerprint (LF)**
  A cryptographic hash of the canonical decoding logic artifact.

* **LogicPayload** (optional)
  The decoding logic itself, typically a WebAssembly module.

### LogicFingerprint Derivation

LogicFingerprint **MUST** be computed over a canonical representation of the logic artifact.
Recommended approaches include:

* Hashing a Wasm binary with non-semantic sections removed
* Hashing a defined canonical Wasm form

The exact canonicalization procedure **MUST** be deterministic.

---

## 2.3.2 Logic Change Marker (LCM)

The **Logic Change Marker (LCM)** identifies the most recent *functional* change in decoding behavior.

LCM is independent of:

* Binary recompilation
* Toolchain changes
* Non-functional rebuilds

### Purpose

* Functional equivalence grouping
* Cache and state reuse decisions
* Observability and debugging

### Recommended Derivation

```
LCM = Truncate( SHA-256( LIM_canonical || FunctionalEquivalenceTag ) )
```

The FunctionalEquivalenceTag **MUST** be included in the signed Upgrade Statement.

---

## 2.3.3 Logic Interface Manifest (LIM)

Each decoding logic implementation **MUST** expose a **Logic Interface Manifest (LIM)**.

The LIM defines the canonical contract between the player and the decoder.

### Required Contents

* Decoder ABI version
* Exported functions and signatures
* Required WebAssembly features
* Optional WebAssembly features
* Canonical serialization and hash

The LIM **MUST** be immutable for a given LogicFingerprint.

### Canonical Encoding

* LIM **MUST** be encoded using CBOR-C14N.

---

## 2.3.4 Logic Reference Mode

Each Atom **MUST** declare how decoding logic is referenced.

**LogicRefMode**

* `embedded`
* `id-only`

If `id-only` is used, the Atom **MUST** include:

* LogicFingerprint
* LogicVersion
* LIM hash

### Logic Resolution Policy

Atoms **MAY** additionally declare a LogicResolutionPolicy:

* `embedded-only`
* `embedded-or-cache`
* `cache-only`
* `cache-or-network-with-pin`

Network retrieval **MUST** be disabled by default unless explicitly enabled by policy.

Logic caches **MUST** be indexed by `(OriginUUID, LogicFingerprint)` and bound to a verified trust anchor.

---

## 2.4 Parameters and Conditional Decoding

### 2.4.1 Parameter Block

Atoms **MAY** include a Parameter Block.

The Parameter Block:

* **MUST** be pure data
* **MUST NOT** contain executable logic
* **MUST** be canonically serializable

Typical uses include:

* View or eye selection
* Resolution or LOD hints
* Temporal or spatial scaling preferences
* Quality vs latency hints

---

## 2.4.2 Capability Introspection (Normative)

Decoding logic **MUST** support capability introspection allowing a player to determine supported features **before decoding**.

Introspection is a **functional requirement**, not tied to any specific API.

---

## 2.4.3 Static and Dynamic Introspection

### Static Capabilities

* Decoders **MUST** expose a static, signed capability declaration.
* Static capabilities **MUST NOT** require executing decoder logic.
* Static capabilities **MUST** be canonically serialized and verifiable.

### Dynamic Introspection (Optional)

* Decoders **MAY** support dynamic introspection queries.
* Dynamic introspection **MUST** execute under strict runtime limits:

  * No network
  * No filesystem
  * No clocks or randomness
  * Instruction and memory quotas

---

## 2.4.4 Introspection Scope

Introspection **MUST** be able to describe:

### Pixel and Sample Formats

* Bit depth
* Component layout
* Chroma subsampling
* Packing and endianness
* Alpha and auxiliary planes

### Image Capabilities

* Encodings
* Color spaces and primaries
* Transfer functions
* HDR signaling
* Resolution limits

### Video Capabilities

* Frame rates
* Interlaced or progressive support
* Temporal reordering
* HDR formats
* Scalable or layered video

### 3D and Spatial Media

* Multi-view layouts
* Depth or geometry streams
* Point clouds or meshes
* Coordinate systems

### Future Media Types

* Unknown media classes
* Vendor extensions
* Custom descriptors

Unknown capabilities **MUST** be treated as opaque structured data.

---

## 2.5 Runtime and Execution Constraints

Decoders **MUST** declare:

* Required WebAssembly features (simd, threads, memory64)
* Recommended memory limits
* State persistence expectations
* Determinism guarantees

All introspection results **MUST** be deterministic and canonically serializable.

---

## 3. Upgrade and Continuity Protocol

### 3.1 Active Logic Selection

Players maintain an **Active Logic Version** per OriginUUID.

Rule:

> The highest accepted LogicVersion becomes active and remains active until replaced by a newer valid version.

Rollback to older versions **MUST NOT** occur unless explicitly permitted by player policy.

---

## 3.2 Version Lineage Chain (VLC)

Decoder upgrades **MUST** be cryptographically linked.

Atoms introducing a higher LogicVersion **MUST** include a signed **Upgrade Statement** containing:

* OriginUUID
* AtomUUID
* ParentLogicFingerprint
* ParentLogicVersion
* NewLogicFingerprint
* NewLogicVersion
* LogicChangeMarker
* LIM hash

Upgrade Statements **MUST** be canonically encoded (CBOR-C14N).

### Signature

* Ed25519 is the recommended signature algorithm.
* The resulting signature is the **LineageSignature**.

---

## 3.3 Anti Man-in-the-Middle and Anti-Rollback Rules

Players **MUST** verify:

1. LogicFingerprint integrity
2. LineageSignature validity
3. Parent-child continuity
4. LogicVersion monotonicity

Failure to verify **MUST** result in upgrade rejection.

Players **SHOULD** persist the highest accepted LogicVersion to prevent rollback attacks.

---

## 3.4 Trust Anchors

Two trust models are defined:

**Model A: Embedded Root Key**
The initial Atom embeds a RootPublicKey.

**Model B: External Trust Store**
The player maintains trusted publisher keys.

Key rotation **MAY** be supported via signed key rotation statements.

---

## 4. Stateful Decoding and Migration

Decoders **MAY** maintain state across Atoms.

### State Handling

* State **MUST** be serializable.
* State serialization format **SHOULD** be CBOR.
* A **StateSchemaHash** **MUST** identify state structure.

### Upgrade Behavior

* If LCM and StateSchemaHash match, direct state reuse is permitted.
* If LCM differs, migration is allowed only if explicitly declared by the decoder.
* Failed migrations **MUST** result in safe state reset.

---

## 5. Conceptual Model: Puddle with Tire Tracks

Decoder upgrades are analogous to puddles with tire tracks on a road.

Each puddle represents a new decoder version that persists forward along the path.
Once passed, the tracks remain. Subsequent Atoms inherit that decoder until a newer puddle appears.

---

## 6. Security Considerations

* WebAssembly execution **MUST** be sandboxed
* Network access **MUST** be disabled by default
* System calls **MUST** be allowlisted
* Resource usage **MUST** be constrained per OriginUUID

Security is a correctness requirement, not an optional feature.

