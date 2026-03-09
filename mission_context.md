# MISSION CONTEXT: Eco-Twin Oracle
**Objective:** Build an interactive, prescriptive control engine for industrial manufacturing. 

**Strict Architectural Directives:**
1. **Mathematical Guardrails (DFA):** State management must be governed by a Deterministic Finite Automaton representing physical manufacturing phases. No arbitrary ML predictions are allowed without passing through the DFA transition matrix to ensure thermodynamic and physical feasibility. 
2. **Soft Computing Core:** AI logic must prioritize Kohonen Self-Organizing Maps (SOM) for topological clustering (Golden Signature) and Learning Vector Quantization (LVQ) for anomaly classification. Do NOT use generic regression models.
3. **Data Structure:** Data ingestion must follow Jackson Structured Design principles, mirroring the chronological time-series lifecycle of the batch entity via WebSockets.
4. **Interoperability:** Backend must be FastAPI with auto-generated Swagger UI (/docs) to expose optimal setpoints. 
5. **UI/UX Standard:** Frontend requires a high-tech dark theme (Navy, Cyan, Neon Green) utilizing Plotly for 60fps rendering, advanced CSS pseudo-classes, and responsive interactions for anomaly alerts.