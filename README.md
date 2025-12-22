# Self Media Decoder (SMD) Specification Version 1.0

## 1\. Abstract and Core Design Philosophy

The **Self Media Decoder (SMD)** standard moves away from the traditional "codecs-in-OS" model toward a **"codecs-in-media"** approach. In SMD, each media file can carry its **own decoder logic** (packaged as a WebAssembly module) alongside the content. This design decouples media decoding from the player's installed codecs, allowing content to **bundle its decompressor with the data** and enabling transparent format evolution and easier adoption of new compression techniques[\[1\]](https://www.vldb.org/pvldb/vol18/p4017-gienieczko.pdf#:~:text=a%20new%20abstraction%3F%20We%20answer,DuckDB%2C%20Spark%2C%20and%20Umbra%2C%20while). Crucially, SMD ensures the decoder maintains **state across fragmented sequences and complex hierarchies** of media, so that context (such as caches or temporal predictions) is preserved when playing segmented or branched content.

A core innovation in SMD is its **Upward Versioning Management** mechanism for decoder logic. This feature enables _"hot-swapping"_ the execution engine during playback: content creators can include **upgraded decoder versions** within a sequence of media segments, thereby seamlessly updating the player's decoding logic for all subsequent segments **without altering or re-encoding any previously delivered content**. In essence, the highest-version decoder in the sequence takes over future decoding, ensuring that improvements in compression or bug fixes can be rolled out mid-stream while maintaining backward compatibility with earlier segments.

## 2\. The SMD Atom: File Structure

An **SMD file** (referred to as an **"Atom"**) is a self-contained media unit that extends a standard container format (such as Matroska .mkv or ISO Base Media File .mp4) with mandatory SMD metadata. These SMD extensions store information about sequence linkage, timing, and embedded decoder logic. By leveraging standard containers, SMD remains compatible with existing storage and transmission systems, while the extra metadata guides SMD-aware players in managing stateful decoding.

### 2.1. Sequence Header (SH)

Every SMD Atom **must** contain a **Sequence Header** structure in its private metadata. The Sequence Header defines the atom's identity and its position in a larger sequence or hierarchy of media. It includes the following fields (typically stored in a container's metadata or header section):

- **AtomUUID:** A unique 128-bit identifier for the current Atom file. This globally unique ID distinguishes this media asset from all others.
- **Linkage (Backward-Only):** Identifiers linking this Atom to its predecessors in a sequence hierarchy:
- **SourceUUID:** The AtomUUID of the immediate previous file in the sequence (the "parent" or source this segment continues from).
- **OriginUUID:** The AtomUUID of the root of the sequence (the very first ancestor in a branching hierarchy). This allows tracing back to the sequence's start.
- **Absolute Sequence Timeline (AST):** Timing information that places this Atom in a global timeline spanning the sequence:
- **AtomStartTime:** The global timestamp (or timeline clock) at which this atom begins playback. This is typically an absolute timestamp or offset from the sequence's start, ensuring all atoms in a sequence share a common time basis.
- **AtomDuration:** The temporal length (duration) of this atom's content in the global timeline. This helps the player understand where the next atom will begin and manage synchronization.

_Rationale:_ The Sequence Header provides enough information for a player to insert this Atom into a continuous playback timeline, even in complex scenarios like branching paths. Notably, the linkage is **backward-referencing only** (each node knows its parent, but not its children), which keeps each file self-sufficient and avoids forward dependencies. This backward-only reference model makes the system robust: even if a manifest is incomplete or some future segments are missing, any given Atom can still be played in sequence by following the chain of SourceUUID back to an origin.

### 2.2. Logic Identity and Versioning

To support evolutionary upgrades of the decoder without requiring changes to already-published content, SMD embeds a **version-aware loading mechanism** for the decoder logic. Each Atom carries metadata identifying which decoder logic to use and if a new decoder module is provided. The **Logic Identity** metadata consists of:

- **LogicVersion (LV):** A version number for the decoder logic. This may be a monotonically increasing integer or a semantic version (SemVer) string. Higher numbers indicate newer versions of the decoder. The version allows the player to compare the decoder in this Atom against any decoder already in use.
- **LogicFingerprint (LF):** A cryptographic hash (fingerprint) of the WebAssembly binary for the decoder. This acts as a unique identifier for the exact code. It enables the player to recognize if it already has the same decoder module loaded or cached (e.g. from a previous Atom in the sequence or local cache), avoiding redundant loading.
- **LogicPayload:** The WebAssembly binary module for the decoder _itself_. This field is **optional** in each Atom:
- If the **LogicPayload is present**, it contains the actual .wasm decoder bytes for this version.
- If **absent**, the player is expected to already have the decoder logic available - either carried over from the **SourceUUID** ancestor or retrieved from a cache by matching the LogicFingerprint. In practice, the first Atom of a sequence will include the decoder payload, while subsequent Atoms might omit it if they use the same decoder or assume the player retained it from earlier.

This design means that content creators can choose whether to ship the decoder with every segment or only when it changes. It also avoids duplication: a long sequence of segments that use the same decoder logic need not repeatedly embed the same Wasm binary, as long as the first segment (or some prior segment) provided it.

## 3\. The Upgrade and Continuity Protocol

SMD enforces a **"Highest Version Wins"** rule for decoder execution when traversing a sequence of one or more Atoms. At playback time, the player uses the following protocol to ensure it always runs the most advanced decoder logic compatible with the content:

- **Version Evaluation:** Upon loading an Atom (whether it's the initial root segment or a randomly accessed node), the player reads the Atom's LogicVersion (LV). It compares this version to the version of the decoder currently in memory (if any). If this is the first Atom being played, there is no decoder yet in memory.
- **Logic Hot-Swap:** If LV_atom > LV_memory (the Atom's decoder version is newer than what the player is currently using), the player **initiates an upgrade**. The current WebAssembly decoder instance is **suspended**, and the new **LogicPayload** from the Atom is loaded (compiled and instantiated). From this point onward, the new decoder logic will be used for decoding the media. This "hot-swap" happens immediately upon encountering a higher version, so that **all subsequent data** (in this Atom and any future Atoms) benefits from the updated logic.
- **State Migration:** To avoid disrupting playback or losing context when switching decoders, SMD-compliant decoder modules are required to implement a state transfer interface. Specifically, the older decoder should expose a function like migrate_state(heap_ptr) which can be invoked to extract or transfer its internal state. The player will call this after instantiating the new decoder, passing in a pointer or blob of the previous state (e.g. memory heap, keyframe indices, learned model weights, buffering caches). The new decoder version can then **ingest the existing state** from the prior version, allowing decoding to continue without a "cold start." This capability is vital if the content has dependencies across segments (for example, predictive frames or accumulated data) - it ensures continuity despite the decoder code change.
- **Persistent Hot State:** If the Atom's LogicVersion is **identical** to the current in-memory version (i.e. no upgrade), the player **reuses the existing WebAssembly instance** and continues decoding. The decoder's internal state (such as bitstream parsing context, reference frames, etc.) carries on seamlessly across the boundary between files. In effect, even though the media was split into multiple files, the decoder experiences it as a single continuous session. SMD requires players to preserve this _hot state_ across file boundaries when no version change occurs. This way, things like inter-frame references or streaming buffers do not reset at each new segment.

Together, these rules guarantee that at any point in a branching sequence, the **latest available decoder logic is active**, while also ensuring that valuable state is carried forward. If a user seeks to a different branch or segment, the Version Evaluation step on that random access will similarly ensure the appropriate decoder (most up-to-date in that context) is loaded and that any previously cached decoder can be reused if it matches the fingerprint.

## 4\. Complex Hierarchies: DAGs and Branching

Beyond simple linear playlists, SMD is designed to handle complex, **non-linear media hierarchies** in which multiple Atoms form a Directed Acyclic Graph (DAG). This allows for interactive or adaptive streaming scenarios (such as multi-angle videos, branching storylines, or quality-bitrate switching). Key aspects of SMD's hierarchy support include:

- **Hierarchical Layout:** Any given Atom may have **multiple "child" Atoms** that continue the sequence in different possible directions. For example, two Atoms might share a common predecessor but diverge into alternate branches (similar to a choose-your-own-adventure story, or switching between camera angles). Conversely, multiple branches might later **converge** back into a single Atom (for instance, a common ending segment reached from different story paths). The DAG structure does not contain cycles (no Atom replays once it's passed), preserving a directed flow of time.
- **Timestamp Synchronization:** Because branching can lead to jumps in the content timeline, each Atom's **AtomStartTime** (from the Sequence Header) is used to align decoder state. When a player jumps from one branch to another (or merges into a converged node), it uses the AtomStartTime to **synchronize the decoder's internal timeline**. This ensures that time-dependent decoder operations (like order of frames or buffered audio) remain correct relative to the overall sequence. Essentially, the decoder can adjust its **temporal priors** or expectations based on the global timeline, so that even after a branch switch, it knows "where it is" in time.
- **Parent-Only Awareness:** An important design principle is that each Atom only needs metadata about its **immediate predecessor** (the SourceUUID). An Atom is **not required to know the identities or existence of any subsequent Atoms** that follow it. This localized knowledge greatly improves robustness and flexibility: you can remove or add branches without modifying other atoms, and a player can handle missing or skipped segments gracefully. If a certain branch's next segment is unavailable (e.g. due to network issues or optional content), the player isn't stuck - it simply knows there are no further links from the last known segment and can terminate that path. This parent-linking scheme eliminates the need for a centralized manifest of the entire graph during playback, as the sequence can be navigated step-by-step.

## 5\. Termination: The EOSQ Signal

An SMD sequence (or a branch of a hierarchy) concludes when it encounters an **End of Sequence** marker, abbreviated **EOSQ**. EOSQ is a metadata signal carried in the final Atom of a sequence/branch to denote clean termination:

- **EOSQ Definition:** EOSQ is represented as a specific marker bit or flag in the Atom's metadata (for example, a flag in the container's last cluster or segment info). When a player reads this marker at the end of an Atom, it indicates that **the current path has ended** - there are no further Atoms linked (this Atom has no children in the DAG). EOSQ essentially says "end of stream" for this branch.
- **State Disposal:** Upon encountering EOSQ, the player knows it can safely **finalize or recycle the decoder instance**. The persistent WebAssembly decoder (and its associated memory state) can be purged from memory since its job is done - unless the same decoder logic (by LogicFingerprint) is also used for other sequences that might play soon, in which case the player might cache the compiled module for efficiency. The EOSQ is the point where the player may release resources like buffers or file handles associated with that sequence. However, SMD does not forbid reusing the decoder: if another sequence starts that requires the _same_ Wasm decoder (identified by matching fingerprint and version), the player can skip re-compiling and use the cached instance, provided it had retained it after EOSQ. This balances cleanup with optimization for subsequent playback.

## 6\. Container Integration Matrix

To implement the above features, SMD leverages custom metadata boxes or elements in existing container formats. The following table summarizes how key SMD concepts map to Matroska (MKV) and ISO Base Media (MP4) file structures:

| **Feature** | **Matroska (MKV) Mapping** | **ISOBMFF (MP4) Mapping** |
| --- | --- | --- |
| **Linkage** | PrevUUID element (stores SourceUUID of previous Atom; serves as authoritative linkage) | Custom UUID box in moof (movie fragment) carrying SourceUUID/OriginUUID references. |
| **Hierarchy** | Ordered Chapters (using Matroska EditionFlagOrdered to denote sequential/branched chapters) | Linked sidx (Segment Index) with subsegment entries indicating branches and their durations. |
| **Logic** | Attachment file: the Wasm binary is embedded as an AttachedFile with FileMediaType = application/wasm (and a FileUID or name to identify it). | Stored in the moov container's meta box as a binary item (e.g., a Meta box entry or a custom atom) containing the Wasm module. |
| **Versioning** | Use Matroska DocType or a custom tag to indicate SMD version requirements (e.g., DocTypeReadVersion could be bumped or an extra element for LogicVersion). | A custom field in a dedicated SMD UUID box (within moov or moof) to record the LogicVersion and perhaps LogicFingerprint. |
| **EOSQ** | Could use a special flag in DocTypeReadVersion or a specific metadata element to mark End-of-Sequence. (For instance, a dummy element at end of file to signal EOSQ.) | Indicated by setting the segment duration to a sentinel value (e.g., 0xFFFFFFFF for an undefined duration) in the final moof, or by a dedicated EOS flag box. |

_Notes:_ These mappings illustrate one way to implement SMD on the two popular container formats: - In Matroska, the extensible EBML structure allows adding new elements or using attachments and chapters to carry SMD info. For example, Matroska attachments already support including arbitrary files (like fonts or images), so including a Wasm decoder is a natural extension. - In MP4/ISOBMFF, the use of uuid (user-defined) boxes is a standard way to include custom metadata. Placing the SMD info in moof (for per-segment data like linkage) and in moov/meta (for global or initialization data like the decoder) keeps SMD data alongside the segments where needed. - The EOSQ via duration 0xFFFFFFFF is analogous to how MP4 signals an indefinite or till-end duration for a segment, effectively marking an end. In practice, a more explicit marker could be used if the format allows.

## 7\. Performance and Optimization

SMD is built on WebAssembly, and to achieve native-like performance and scalability in decoding, the specification mandates support for the latest WebAssembly features and parallelism models:

- **Relaxed SIMD:** Decoders should utilize WebAssembly 3.0's **Relaxed SIMD** instructions for vectorized operations. Relaxed SIMD offers flexibility in implementation-defined behavior for certain edge cases, which allows engines to optimize for **maximum hardware throughput**[\[2\]](https://www.x-cmd.com/blog/250924/#:~:text=,exchange%20for%20higher%20execution%20efficiency). By using these relaxed vector instructions, SMD decoders can achieve extremely high performance (on the order of 90% or more of native machine code speed) by leveraging CPU SIMD extensions without being bottlenecked by strict deterministic requirements. This is particularly important for video/image decoding or neural-network-based compression, where heavy math can be parallelized.
- **Memory64:** SMD mandates **WebAssembly Memory64** support, meaning the decoder can utilize a 64-bit address space for its linear memory. This lifts the 4 GB memory limit of 32-bit WebAssembly memories, allowing addressable heaps well beyond 4 GB (up to 16 exabytes theoretically[\[3\]](https://webassembly.org/news/2025-09-17-wasm-3.0/#:~:text=%2A%2064,applications%20and%20data%20sets%20now), though practical limits are lower). The Memory64 requirement is crucial for handling **very large media** or long-running stateful sessions - for example, 8K resolution video frames, or long DAG sequences that accumulate substantial data. With a 64-bit memory, decoders can buffer large content or numerous reference frames without running into address space constraints.
- **Parallel Execution:** SMD-compliant players **must support multi-threaded WebAssembly** execution (via the WebAssembly threads proposal and **WASI-threads** API) to enable decoding across multiple CPU cores. Many codec algorithms (e.g., video decoding, AI-based enhancers) benefit from parallelism. WASI-threads is a standardized way for WebAssembly modules to spawn threads in non-browser environments[\[4\]](https://bytecodealliance.org/articles/wasi-threads#:~:text=Until%20now%2C%20one%20piece%20missing,threads%20drastically%20improves%20performance), complementing the WebAssembly threads core spec (which enables shared memory and atomics). By utilizing threads, an SMD decoder could, for instance, decode multiple chunks of a frame in parallel or perform background optimization tasks. The player's runtime must therefore allow the Wasm module to create and manage threads (respecting security and sandboxing), yielding performance that scales with available CPU cores. This requirement aligns with modern multimedia frameworks where multi-core decoding is standard for high-resolution, high-bitrate content.

In summary, the SMD standard is designed to marry the **flexibility of web-era software** (WebAssembly's portability and safety) with the demands of modern media streaming. It treats media files as active objects that carry their intelligence (decoder logic) with them. This approach is in line with emerging research and standards aiming for self-contained, **stateful streaming**. For example, the database community's _AnyBlox_ framework similarly bundles decoders with datasets to allow format evolution on the fly[\[1\]](https://www.vldb.org/pvldb/vol18/p4017-gienieczko.pdf#:~:text=a%20new%20abstraction%3F%20We%20answer,DuckDB%2C%20Spark%2C%20and%20Umbra%2C%20while), and in the MPEG immersive media arena, current work on _scene-based media representation_ (MPEG-I Part 28) is developing architectures for sending interactive 3D scene content with the necessary logic for rendering[\[5\]](https://www.mpeg.org/standards/MPEG-I/28/#:~:text=Edition%20,based%20systems%20and%20applications). SMD extends these ideas to general multimedia: it ensures that **when you press play, the content itself can dictate how it should be decoded**, optimizing compatibility and performance across diverse devices and future formats.

[\[1\]](https://www.vldb.org/pvldb/vol18/p4017-gienieczko.pdf#:~:text=a%20new%20abstraction%3F%20We%20answer,DuckDB%2C%20Spark%2C%20and%20Umbra%2C%20while) vldb.org

<https://www.vldb.org/pvldb/vol18/p4017-gienieczko.pdf>

[\[2\]](https://www.x-cmd.com/blog/250924/#:~:text=,exchange%20for%20higher%20execution%20efficiency) x-cmd blog (daily) | \[250924\] WebAssembly 3.0 Officially Released: Major Features like GC, 64-bit Memory, and Exception Handling Arrive

<https://www.x-cmd.com/blog/250924/>

[\[3\]](https://webassembly.org/news/2025-09-17-wasm-3.0/#:~:text=%2A%2064,applications%20and%20data%20sets%20now) Wasm 3.0 Completed - WebAssembly

<https://webassembly.org/news/2025-09-17-wasm-3.0/>

[\[4\]](https://bytecodealliance.org/articles/wasi-threads#:~:text=Until%20now%2C%20one%20piece%20missing,threads%20drastically%20improves%20performance) Bytecode Alliance - Announcing wasi-threads

<https://bytecodealliance.org/articles/wasi-threads>

[\[5\]](https://www.mpeg.org/standards/MPEG-I/28/#:~:text=Edition%20,based%20systems%20and%20applications) Standards - MPEG

<https://www.mpeg.org/standards/MPEG-I/28/>