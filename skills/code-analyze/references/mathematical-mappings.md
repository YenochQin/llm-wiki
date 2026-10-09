# Mathematical Mappings for Code

Read this reference when translating traced code operations into LaTeX. Paths and commands below are relative to the llm-wiki repository root unless an external root is explicitly named.

Define symbols before using them. Start with the global pipeline:

$$
x_0 \xrightarrow{T_1} x_1 \xrightarrow{T_2} \cdots
\xrightarrow{T_n} x_n,
\qquad
x_n = (T_n \circ T_{n-1} \circ \cdots \circ T_1)(x_0).
$$

Then give at least one meaningful LaTeX expression for every substantive processing stage. Match
the expression to the code semantics:

- transformation: $x_i = T_i(x_{i-1}; \theta_i)$;
- branch: $x_i = \begin{cases}T_i^{(a)}(x_{i-1}), & c(x_{i-1}) \\ T_i^{(b)}(x_{i-1}), & \text{otherwise}\end{cases}$;
- iteration: $s_{k+1} = F(s_k, u_k)$;
- aggregation: $z = \sum_{j=1}^{m} w_j h_j$ or the exact implemented reducer;
- normalization: write the implemented denominator, axes, constants, and epsilon explicitly;
- optimization: state the implemented objective and update rule separately;
- stochastic processing: state the distribution or sampling rule only when present in code;
- reshape, indexing, filtering, or concatenation: specify shape and index mappings;
- I/O or orchestration with no numerical computation: use a typed mapping or state transition,
  such as $(s_{k+1}, o_k) = T(s_k, i_k)$.

Do not invent an algorithm, objective, probability model, variable meaning, or equation that the
code does not support. If a stage cannot be reduced to a useful numeric formula, formalize its
mapping, predicate, or state transition and explain the limitation.
