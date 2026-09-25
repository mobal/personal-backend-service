"""Seed 50 tech posts via the local API for frontend testing.

Usage: uv run python scripts/seed_test_posts.py
"""

import json
import os
import time
import urllib.request

BASE = "http://localhost:8080/api/v1/posts"
TOKEN = os.environ["SEED_AUTH_TOKEN"]

AUTHOR = "Balázs Molnár"

# (year, month, day, hour, title, tags, description, content)
POSTS = [
    # ---- 2025-12 ----
    (
        2025,
        12,
        2,
        9,
        "Android 16 QPR2: what actually changed for developers",
        ["android", "mobile", "google"],
        "A hands-on look at the latest Android quarterly release and what it means for app developers.",
        """I spent the weekend updating my apps against the newest Android quarterly release, and there is more here than the changelog suggests.

The predictive back gesture is now enforced by default, which broke one of my custom navigation transitions. The fix was straightforward but it reminded me how long we have been living on borrowed time with that opt-in flag.

Other things worth noting:

- Background work restrictions got tighter again; JobScheduler is now the only sane option
- The new photo picker APIs finally feel complete
- Baseline Profiles continue to be the cheapest performance win available

If you ship on Android, budget an afternoon for this one.""",
    ),
    (
        2025,
        12,
        5,
        14,
        "Rust in 2026: my wishlist after a year of shipping it",
        ["rust", "programming"],
        "Reflections on a year of production Rust and what I hope the ecosystem focuses on next year.",
        """A year ago I moved our most performance-sensitive service to Rust, and it has been quietly doing its job ever since. That is the highest praise I can give: nobody thinks about it anymore.

My wishlist for the ecosystem next year:

1. Faster builds. Incremental compile times are better, but cold builds still hurt.
2. Better async ergonomics for newcomers. The pinning mental model is still a wall.
3. More stabilization in the embedded space.

The language itself is in a good place. The borrow checker stopped being news to me around month three, and now it just catches real bugs before they ship.""",
    ),
    (
        2025,
        12,
        9,
        10,
        "Local LLMs in December 2025: what fits on a laptop",
        ["ai", "llm", "machine-learning"],
        "Testing the current generation of small open models on consumer hardware.",
        """I ran a bake-off of the current small open models on my laptop this week. The gap between local and cloud models keeps shrinking.

What surprised me:

- 8B-class models now handle structured output reliably enough for real pipelines
- Quantization has almost stopped mattering for quality below 4-bit
- Context handling is the new differentiator, not raw parameter count

For coding assistance the local models are still a tier behind, but for summarization, classification, and drafting they are genuinely good enough. The privacy win alone justifies it for anything touching user data.""",
    ),
    (
        2025,
        12,
        12,
        16,
        "iOS 26.2 deep dive: the small fixes that matter",
        ["ios", "swift", "apple"],
        "The point release nobody talks about, with fixes that actually affect shipping apps.",
        """Point releases rarely get write-ups, but 26.2 fixed two things that were actively annoying my users: a background refresh regression and a keyboard focus bug in collection views.

Notes from updating:

- StoreKit transaction handling got a subtle behavior change; test your restore flow
- The new design system APIs are stable enough to adopt incrementally
- Widget reload budgets seem more generous, or at least less punishing

Small release, but if you have been holding off, this is a safe one.""",
    ),
    (
        2025,
        12,
        16,
        11,
        "TypeScript 6: narrowing down what I actually use",
        ["typescript", "javascript", "programming"],
        "How the latest TypeScript release changes day-to-day frontend work.",
        """The newest TypeScript release landed and my favorite feature is not flashy: it is the improved narrowing for discriminated unions with optional fields. Half my runtime bugs used to live exactly there.

Also worth adopting:

- `satisfies` everywhere you previously reached for `as`
- The faster incremental mode, which is noticeably snappier on our monorepo
- Stricter inference in conditional types, which broke two of our utility types in a good way

Migration took an afternoon across a large codebase. Worth it.""",
    ),
    (
        2025,
        12,
        19,
        13,
        "Postgres 18 in production: three months later",
        ["database", "postgres", "backend"],
        "Real-world experience after upgrading our main database to Postgres 18.",
        """We upgraded our primary Postgres cluster to version 18 three months ago, and I wanted to share what actually happened instead of what the release notes promised.

The async I/O change is real. Our read-heavy endpoints got measurably faster without any query changes. Skip scan helped one of our worst indexes disappear entirely.

The gotchas:

- One extension needed a manual rebuild
- Logical replication slots needed re-verification after the upgrade
- Plan changes hit two queries; `pg_hint_plan` saved us while we rewrote them

Overall the smoothest major upgrade we have done.""",
    ),
    (
        2025,
        12,
        23,
        10,
        "Kubernetes without the ceremony: my minimal setup",
        ["kubernetes", "devops", "cloud"],
        "Stripping a Kubernetes setup down to what a small team actually needs.",
        """Every year I try to delete things from our Kubernetes setup, and every year I succeed. This December's pass removed an entire service mesh.

What the minimal stack looks like now:

- A managed control plane, because running masters is a hobby, not a job
- One ingress controller, configured once, never touched
- Kustomize overlays instead of a Helm chart with 400 values

The lesson after years of this: every component you add is a component that pages you at 3am. Add things when the pain is real, not when the conference talk is compelling.""",
    ),
    (
        2025,
        12,
        29,
        15,
        "Year in review: the tools that earned their keep in 2025",
        ["tools", "productivity", "retrospective"],
        "A look back at the developer tools that actually stuck throughout the year.",
        """End of year, so here is the honest list: tools I adopted in 2025 that I still use daily, which is the only metric that matters.

- uv replaced every Python tool I had, and I have not looked back once
- Zed became my daily editor for everything except debugging
- A single 40-dollar mechanical keyboard fixed more wrist pain than any ergonomic mouse

And the failures: three note-taking apps, two task managers, and a self-hosted analytics stack that lasted six weeks. The pattern is clear — the tools that stick solve one problem completely.""",
    ),
    # ---- 2026-01 ----
    (
        2026,
        1,
        5,
        9,
        "Starting 2026 with Swift 6.2: concurrency without fear",
        ["swift", "ios", "concurrency"],
        "How Swift's latest concurrency improvements changed our migration story.",
        """New year, new Swift. We finally started migrating our largest app to strict concurrency over the holidays, and 6.2 made it dramatically less painful than the horror stories from two years ago.

The default MainActor isolation mode means most of our UI code just compiles. The remaining work was in our networking layer, where `Sendable` conformance forced us to be honest about shared mutable state.

Two bugs found during migration paid for the whole effort: a data race in our image cache and a subtle ordering issue in offline sync. Strict concurrency is not ceremony; it is a bug finder.""",
    ),
    (
        2026,
        1,
        8,
        14,
        "Go 1.26 generics: patterns that finally click",
        ["go", "programming"],
        "Practical generic patterns in Go after the language matured around them.",
        """Generics in Go took a while to find their identity, but with the latest release the standard library itself uses them enough that idiomatic patterns have emerged.

The patterns I actually use:

- Generic container types with method constraints, not free functions
- `constraints` packages per domain, keeping type lists close to their usage
- Generic repository interfaces that still expose concrete types at the edges

What I still avoid: generic inheritance games and type-level metaprogramming. Go's strength was never cleverness. The best Go code I read this year was boring, and I mean that as praise.""",
    ),
    (
        2026,
        1,
        12,
        10,
        "AI agents in 2026: from demos to boring production",
        ["ai", "agents", "engineering"],
        "What changed when AI agents moved from impressive demos to production tooling.",
        """The most interesting thing about AI agents this year is how boring they became. Not in capability — in reliability engineering.

Our internal agent that triages support tickets now has:

- Structured outputs validated against schemas, no free-form parsing
- A replayable event log for every run
- Hard budgets on tool calls and tokens
- A human approval step for anything that writes to production

The capability was there a year ago. What was missing was treating agents like distributed systems instead of magic. Once we added observability and failure budgets, they became deployable.""",
    ),
    (
        2026,
        1,
        15,
        16,
        "Android's new build pipeline: Gradle finally gets fast",
        ["android", "gradle", "build"],
        "Benchmarking the configuration cache and isolated projects on a real codebase.",
        """I have complained about Gradle build times for a decade, so it is only fair I write about the other side. After enabling the configuration cache and isolated projects on our mid-sized app, clean builds dropped from 6 minutes to under 2.

The migration was not free:

- Two plugins needed updates for configuration cache compatibility
- Our build logic had hidden cross-project state that had to be untangled
- CI needed a bigger cache, which paid for itself in a week

If your team loses an hour a day to builds, this is the highest-leverage week of work you can do this quarter.""",
    ),
    (
        2026,
        1,
        19,
        11,
        "Python 3.14 in production: the free-threading experiment",
        ["python", "backend", "performance"],
        "Running a Python service on the free-threaded build for a month.",
        """We ran one of our CPU-bound Python services on the free-threaded 3.14 build for a month. Results, honestly reported:

For our workload — JSON-heavy request handling with some image processing — throughput improved about 2.3x on 4 cores. Not the ideal linear scaling, but we did not change a line of code.

The friction points:

- One C extension was not yet compatible; we replaced it with a pure-Python fallback
- Memory usage went up roughly 15 percent
- Profiling tools are still catching up

For I/O-bound services the GIL was never the problem. But if you have CPU-bound Python, the future is finally here.""",
    ),
    (
        2026,
        1,
        22,
        13,
        "Designing an offline-first mobile app in 2026",
        ["mobile", "architecture", "sync"],
        "Lessons from building sync that survives flaky networks and conflicting edits.",
        """Offline-first used to mean a local database and prayer. The tooling has matured to the point where the hard part is no longer storage — it is conflict resolution and UX.

Our current architecture:

- Local-first storage with an append-only operation log
- Server-side reconciliation with last-writer-wins per field, not per record
- UI that shows sync state honestly instead of pretending everything is instant

The biggest lesson: users do not care about your sync architecture, they care that the app never shows a spinner when they are on the subway. Design for the subway first, and the architecture follows.""",
    ),
    (
        2026,
        1,
        26,
        9,
        "Terraform at 3am: making infrastructure changes safe",
        ["terraform", "devops", "infrastructure"],
        "The guardrails we added after one too many scary terraform applies.",
        """After one memorable 3am incident involving a mis-typed variable and a deleted subnet, we added guardrails to our Terraform workflow. None of them are clever; all of them work.

- Plan output posted to the PR, reviewed like code
- Separate state per environment, no shared state ever
- A `prevent_destroy` on everything with data
- Scheduled drift detection, because silent drift is how surprises happen

Infrastructure code has a property application code does not: a mistake can take down the thing that lets you fix the mistake. Treat it accordingly.""",
    ),
    (
        2026,
        1,
        30,
        15,
        "The case against microservices for small teams",
        ["architecture", "backend", "teams"],
        "Why we consolidated six services into one modular monolith and shipped faster.",
        """We consolidated six microservices into one modular monolith last quarter. Deployment went from a coordinated dance to a single pipeline. Latency dropped because network hops disappeared. Onboarding a new engineer went from two weeks to two days.

The rule I now use: microservices solve an organizational problem, not a technical one. If you have three engineers, you do not have that problem. You have a different problem, and it is usually that everything is too complicated.

Keep the module boundaries inside the codebase. If you ever genuinely need to split, clean boundaries make that a refactor, not a rewrite.""",
    ),
    # ---- 2026-02 ----
    (
        2026,
        2,
        3,
        10,
        "iOS widgets in 2026: interactive, fast, and finally worth it",
        ["ios", "swiftui", "widgets"],
        "Rebuilding our home screen widgets with the latest interactive APIs.",
        """We rebuilt all our widgets with the interactive API this month, and the engagement numbers changed our minds about widgets as a feature. They went from a nice-to-have to a top-three acquisition surface.

What worked:

- Interactive buttons for the single most common action, nothing more
- Timeline budgets respected religiously — stale widgets destroy trust
- Deep links that land exactly on the state shown in the widget

The mistake we made first time: trying to show everything. A widget is a glance, not a dashboard. One number, one action.""",
    ),
    (
        2026,
        2,
        6,
        14,
        "Vector databases are becoming a feature, not a product",
        ["ai", "database", "search"],
        "Why we moved embeddings into our existing Postgres and deleted a service.",
        """Two years ago the advice was unambiguous: dedicated vector database. This month we deleted ours and moved embeddings into Postgres with pgvector.

Why the calculus changed:

- Our scale (tens of millions of vectors) is well within pgvector's comfort zone
- HNSW indexes in Postgres got fast enough that the dedicated service won on latency by single-digit milliseconds
- One fewer service means one fewer thing to operate, secure, and back up

At serious scale — hundreds of millions of vectors, heavy QPS — dedicated engines still win. But the default answer for most teams should now be: use your existing database first.""",
    ),
    (
        2026,
        2,
        10,
        9,
        "Kotlin 2.3: the compiler rewrite pays off",
        ["kotlin", "android", "programming"],
        "What the K2 compiler generation means for build times and language features.",
        """The K2 compiler generation has fully landed in Kotlin 2.3, and the promise is finally delivered on our codebase: builds are around 30 percent faster and error messages point at the actual problem.

New language features worth noting:

- Guard conditions in `when` expressions cleaned up several of our validation functions
- Improved smart casting after `&&` conditions
- Context parameters stabilized, which changes how we think about dependency injection

If you were waiting for the ecosystem to catch up before upgrading, it has. Compose, serialization, and the major libraries are all on board.""",
    ),
    (
        2026,
        2,
        13,
        16,
        "Observability on a budget: traces before dashboards",
        ["observability", "devops", "opentelemetry"],
        "How we got 80 percent of the debugging value from 20 percent of the tooling.",
        """Small teams often skip observability because the enterprise tooling is expensive and complicated. Our approach after trimming our stack: distributed traces first, everything else later.

With OpenTelemetry and a self-hosted collector we get:

- The actual path of a slow request, across services
- Error rates per endpoint without building dashboards
- Sampling that keeps all errors and 1 percent of successes

We added metrics only where traces showed repeated questions, and alerts only where metrics showed repeated page-worthiness. Tooling should follow questions, not precede them.""",
    ),
    (
        2026,
        2,
        17,
        11,
        "Fine-tuning vs RAG in 2026: the decision got easier",
        ["ai", "llm", "machine-learning"],
        "A practical decision framework after shipping both approaches this year.",
        """We shipped both a fine-tuned model and a RAG pipeline this year for different problems, and the decision framework that emerged is simpler than the discourse suggests.

Fine-tune when: you need a specific style or format, the knowledge is stable, and you have thousands of clean examples.

Use RAG when: the knowledge changes, you need citations, or you cannot afford a training loop.

What we almost got wrong: fine-tuning for knowledge. It works until the knowledge changes, and then you are retraining on a schedule. RAG's retrieval is a feature, not a hack — being able to show your sources is worth more than a few points of benchmark accuracy.""",
    ),
    (
        2026,
        2,
        20,
        13,
        "WebAssembly on the server: one year of running it in prod",
        ["wasm", "backend", "cloud"],
        "Honest assessment of server-side WebAssembly after a year of production use.",
        """We run our plugin system on server-side WebAssembly, and after a year I can report: it is excellent for exactly one thing, and that thing is running untrusted code with predictable resource limits.

The wins:

- Sandboxing that actually holds — plugins cannot touch anything we do not hand them
- Cold starts measured in microseconds
- One plugin binary runs on every architecture we deploy

The costs:

- Host-guest communication is still clunky; the component model helps but is not finished
- Debugging across the boundary remains painful
- Performance for compute-heavy work is good, not great

For our use case — third-party extensions — the trade was obviously right.""",
    ),
    (
        2026,
        2,
        24,
        9,
        "Feature flags without the mess: a cleanup story",
        ["engineering", "testing", "process"],
        "How we went from 200 stale flags to 30 live ones, and what we learned.",
        """We audited our feature flags last month and found 200 of them. Roughly 170 were permanently on, permanently off, or referencing features nobody remembered. Each one was a code path untested in its current state.

The cleanup:

- Every flag got an owner and an expiry date at creation
- Flags older than 90 days trigger a removal ticket automatically
- We test both sides of any flag that survives review

The deeper lesson: feature flags are deferred decisions, and decisions deferred forever become technical debt with a runtime cost. Delete aggressively.""",
    ),
    (
        2026,
        2,
        27,
        15,
        "Serverless in 2026: where it wins and where it bites",
        ["serverless", "aws", "cloud"],
        "A cost and performance retrospective on five years of Lambda-based architecture.",
        """This blog's backend has run on Lambda for five years, so here is the long-term view the launch posts could not give you.

Where serverless won decisively: spiky traffic, scheduled jobs, API backends with modest and variable load. My costs track my usage almost perfectly, and I have paged for capacity exactly zero times.

Where it bites: sustained high throughput (provisioned concurrency erodes the cost story), anything latency-critical (cold starts are better but not gone), and long-running tasks.

The 2026 answer is not serverless versus servers. It is matching each workload to its runtime and not feeling ideological about it.""",
    ),
    # ---- 2026-03 ----
    (
        2026,
        3,
        3,
        10,
        "Spring cleaning your CI pipeline: from 40 to 8 minutes",
        ["ci", "devops", "testing"],
        "How we cut our CI time by 80 percent without losing coverage.",
        """Our CI pipeline had crept to 40 minutes, which is long enough that engineers context-switch and never come back. A week of work got it to 8.

The changes, in order of impact:

1. Parallelized the test suite across shards — biggest single win
2. Cached dependencies and build artifacts properly (we thought we had; we had not)
3. Split the slow end-to-end suite to run only on merge, not per-commit
4. Deleted three jobs that checked things the linter already checked

Fast CI is a feature. When feedback arrives in minutes, small PRs become the natural workflow, and everything downstream improves.""",
    ),
    (
        2026,
        3,
        6,
        14,
        "Android Compose performance: measuring before optimizing",
        ["android", "jetpack-compose", "performance"],
        "A systematic approach to finding real Compose performance problems.",
        """Compose makes it easy to write slow UI without noticing, and it makes it equally easy to optimize the wrong thing. We spent a sprint on performance with a strict rule: no change without a measurement.

What the profiler actually found:

- Our biggest jank source was not recomposition — it was image decoding on the main thread
- Unstable lambda parameters caused one list to recompose entirely on every scroll frame
- A single `derivedStateOf` fixed a calculation that ran 60 times per second

The lesson generalizes: intuition about UI performance is bad. The profiler is good. Use the profiler.""",
    ),
    (
        2026,
        3,
        10,
        9,
        "Prompt engineering is becoming context engineering",
        ["ai", "llm", "engineering"],
        "Why the interesting work moved from crafting prompts to designing context.",
        """The term prompt engineering is aging badly. The prompts themselves are the easy part — a few sentences of instruction. The hard part, where all the quality lives, is what you put around them.

Our production LLM features improved more from context work than from any prompt change:

- Retrieval that pulls the right three documents instead of the top ten
- Structured state summaries instead of raw conversation dumps
- Examples chosen per-request rather than baked in

The model is a function; context is the input. Spend your effort where the variance is.""",
    ),
    (
        2026,
        3,
        13,
        16,
        "SwiftData vs Core Data: choosing in 2026",
        ["ios", "swift", "persistence"],
        "A pragmatic comparison after shipping both in production apps.",
        """We have one app on SwiftData and one still on Core Data, and after a year of maintaining both, here is the honest comparison.

SwiftData is genuinely nicer to write. The Swift-native API, the macro-based models, the SwiftUI integration — all real improvements. For a new app with straightforward persistence needs, use it.

Core Data still wins when: you need mature migration tooling, you have complex fetch logic, or you need the performance tuning options that SwiftData does not yet expose.

The migration path between them is real but not free. Do not migrate an existing, working Core Data stack out of fashion. Fashion is not a requirement.""",
    ),
    (
        2026,
        3,
        17,
        11,
        "The two-hour deploy: automating our release process away",
        ["devops", "automation", "release"],
        "How we turned a manual release checklist into a single command.",
        """Our release process used to be a two-hour checklist in a wiki page, executed by whoever drew the short straw. Every step was automatable; none of them were automated. Classic.

The new pipeline does in 12 minutes what took 120:

- Version bump and changelog generated from conventional commits
- Build, test, and sign in one pipeline with artifacts uploaded automatically
- Rollout is gradual by default, with automatic halt on error-rate regression

The meta-lesson: every manual step in a release process is a future incident with a scheduled date. Automate the checklist, then delete the wiki page.""",
    ),
    (
        2026,
        3,
        20,
        13,
        "Reading the source: what I learned from a week in CPython",
        ["python", "open-source", "programming"],
        "Spending a week inside the CPython interpreter to answer one performance question.",
        """I had a performance question no blog post answered, so I spent a week reading CPython source. Two takeaways: the code is more readable than I feared, and my mental model of the interpreter was wrong in useful ways.

Things that surprised me:

- The specializing interpreter means most bytecode you write never executes generically
- Object layout is far more compact than the "everything is a heap object" summary suggests
- The contributing workflow is genuinely welcoming; my small doc fix was merged in two days

If you use a language professionally, reading its implementation once is worth a dozen conference talks. You stop guessing about performance.""",
    ),
    (
        2026,
        3,
        24,
        9,
        "Zero-downtime database migrations: the full playbook",
        ["database", "postgres", "backend"],
        "Every technique we use to change schema without maintenance windows.",
        """We have not had a maintenance window for schema changes in two years. The playbook that makes this possible, in order of operations:

1. Expand: add the new column/table as nullable or with defaults
2. Backfill in batches, rate-limited, with progress tracking
3. Dual-write during the transition, read from old
4. Flip reads to new, verify with shadow reads
5. Contract: remove the old column only after a full cycle of confidence

The unglamorous truth: the migrations themselves are easy. The discipline — never combining steps, always shipping rollback plans — is the hard part. Write the steps down. Follow them slowly.""",
    ),
    (
        2026,
        3,
        27,
        15,
        "API design review: fixing our worst endpoint",
        ["api", "design", "backend"],
        "A case study in evolving a public API without breaking clients.",
        """We had an endpoint that returned a 12-field response where clients used 2, took 800ms, and had a pagination bug we had shipped around for two years. This month we fixed it without breaking anyone.

The evolution strategy:

- New endpoint at a new path, old one kept alive with a deprecation header
- Response includes a `Deprecation` and `Sunset` header, per the RFC
- Usage telemetry told us exactly which clients still called the old path; we emailed each one with their specific migration diff
- Old endpoint returns 410 only after zero traffic for 60 days

APIs are promises. The way you keep them while moving forward is patience plus telemetry.""",
    ),
    # ---- 2026-04 ----
    (
        2026,
        4,
        3,
        10,
        "Multimodal AI in production: beyond the demo",
        ["ai", "multimodal", "engineering"],
        "What it takes to run vision and audio models reliably in real products.",
        """Multimodal models demo beautifully and deploy messily. We run document understanding in production, and the gap between the demo and the pipeline was mostly unglamorous engineering.

What the production system needed that the demo did not:

- Confidence scoring per field, with human review queues for low-confidence extractions
- Preprocessing that handles the scans people actually send: skewed, coffee-stained, photographed at an angle
- A golden dataset built from real failures, not benchmark downloads

The models are ready. The question is whether your pipeline treats them like the probabilistic components they are.""",
    ),
    (
        2026,
        4,
        7,
        14,
        "Android 17 preview: first impressions",
        ["android", "mobile", "google"],
        "Early notes from installing the first Android 17 developer preview.",
        """I flashed the first Android 17 developer preview on my secondary device this week. Early days, but the shape of the release is visible.

Highlights so far:

- Continued push on background restriction — audit your work now, not at launch
- New adaptive refresh rate APIs that should help battery on media-heavy apps
- Privacy dashboard additions that will require some permission UX updates

Standard preview advice applies: install on a spare device, expect breakage, file issues early. The feedback you give now is the API stability you get in the fall.""",
    ),
    (
        2026,
        4,
        10,
        9,
        "The forgotten art of writing a good error message",
        ["engineering", "ux", "backend"],
        "Error messages are your product's customer service voice. Most are terrible.",
        """We audited every error message in our product last month. The most common one was "Something went wrong," which is the software equivalent of a shrug.

The rules we now follow:

- Say what happened, in the user's vocabulary, not the stack trace's
- Say what they can do about it, if anything
- Log the technical detail internally; show the human summary externally
- Never blame the user ("Invalid input" → "Dates must be in the future")

Good error messages are cheap to write and compound: fewer support tickets, more user trust, faster debugging. It is the highest ROI writing you will do this quarter.""",
    ),
    (
        2026,
        4,
        14,
        16,
        "Rust for backend services: one year, three services",
        ["rust", "backend", "programming"],
        "A year-long retrospective on running Rust services in a mostly-Python shop.",
        """A year ago we started writing backend services in Rust alongside our Python stack. Three services later, here is the scorecard.

The wins are real: memory usage down 80 percent on the same workload, p99 latency cut in half, and a category of deployment anxiety (memory leaks, connection pool exhaustion) that simply vanished.

The costs are real too: development velocity for CRUD-heavy work is maybe half of Python's, hiring is harder, and compile times still test patience on CI.

Our rule now: Rust for the hot paths and the stateful services, Python for everything else. Polyglot is not a failure of discipline; it is matching tools to problems.""",
    ),
    (
        2026,
        4,
        17,
        11,
        "Testing AI features: the eval suite changed how we ship",
        ["ai", "testing", "quality"],
        "Building an evaluation pipeline that made LLM features deployable.",
        """We used to ship LLM features by vibes: try ten inputs, looks good, deploy. Then we built an eval pipeline, and shipping got slower and better.

The pipeline:

- A growing dataset of real inputs with graded expected outputs
- Every prompt or model change runs the full set in CI
- Scores tracked over time, with regressions blocking merge just like test failures

The counterintuitive part: the evals do not need to be perfect. Even a rough grading caught enough regressions to pay for itself in the first month. Imperfect measurement beats vibes.""",
    ),
    (
        2026,
        4,
        21,
        13,
        "Home lab 2026: self-hosting in the age of the cloud",
        ["self-hosting", "devops", "hardware"],
        "What I run at home in 2026, what I gave up on, and why.",
        """My home server turned five this year, so an inventory of what survived.

Still running and worth it: media server, photo backup, home automation, a small Kubernetes node for experiments. These are set-and-forget workloads where self-hosting costs me an hour a quarter.

Given up on: self-hosting email (never again), anything my family depends on for communication, and databases I would have to restore under stress.

The dividing line I have converged on: self-host things where downtime is an inconvenience, rent things where downtime is a crisis. The cloud is expensive; being paged about your own photo backup is more expensive.""",
    ),
    (
        2026,
        4,
        24,
        9,
        "The state of cross-platform mobile in 2026",
        ["mobile", "flutter", "react-native"],
        "Evaluating Flutter and React Native after a year of shipping on both.",
        """We shipped features on both Flutter and React Native this year, which is more exposure than any team should have. Comparative notes:

Flutter's tooling and consistency remain its superpower. The same code renders the same everywhere, and the widget model makes custom UI fast to build. The cost is bundle size and a visual style that needs work to feel native.

React Native's new architecture delivered on the promises: the bridge bottleneck is gone, and JS-native interop is smooth. The cost is dependency churn — the ecosystem moves fast, sometimes underneath you.

Both are production-grade. Choose based on your team's existing language skills more than any technical delta.""",
    ),
    (
        2026,
        4,
        28,
        15,
        "Backpressure: the distributed systems concept you keep rediscovering",
        ["architecture", "backend", "reliability"],
        "Why every overload incident is secretly a backpressure problem.",
        """Post-incident reviews have a pattern: the system received more work than it could process, queues grew, latency climbed, and then something cascaded. Every one of these is a backpressure problem wearing a different costume.

The toolkit, from best to worst:

- Load shedding: reject work early, with a clear error, before you drown
- Bounded queues: unbounded queues convert overload into out-of-memory
- Rate limiting at the boundary: protect the core, degrade the edges
- Retries with jitter and budgets: naive retries are a DDoS you send yourself

The cultural part is harder than the technical part: saying no to work must be a designed, tested behavior, not an emergency improvisation.""",
    ),
    # ---- 2026-05 ----
    (
        2026,
        5,
        2,
        10,
        "WWDC predictions and prep: getting ready for June",
        ["ios", "apple", "wwdc"],
        "How I prepare for WWDC so the week is productive instead of overwhelming.",
        """WWDC is two months out, which means now is the time to prepare, not during the keynote.

My prep checklist:

- Audit which OS versions my apps support; decide now what I will drop
- Clear the backlog of small bugs so June can be about adoption, not catch-up
- Set up a test device plan — which hardware gets which beta
- Block actual calendar time in the following weeks; keynote week is marketing, the real work starts after

The teams that adopt new APIs fast get the marketing win. That speed is decided in May, not June.""",
    ),
    (
        2026,
        5,
        5,
        14,
        "Postgres partitioning: when to split and when to stop",
        ["database", "postgres", "performance"],
        "A practical guide to table partitioning based on three real migrations.",
        """Partitioning is one of those tools that is either transformative or a self-inflicted wound, with little middle ground. After three migrations, my threshold: partition when a table exceeds roughly 100 million rows AND your queries naturally filter by the partition key. Both conditions, not either.

What worked for us:

- Range partitioning by month for time-series data, with automated partition creation
- Dropping old partitions instead of deleting — instant, no bloat
- Keeping partition counts under a few hundred; the planner degrades gracefully but noticeably

What did not: partitioning a table where half the queries lacked the partition key. Every query became a scan of every partition. Measure first.""",
    ),
    (
        2026,
        5,
        8,
        9,
        "The AI code review assistant: three months of data",
        ["ai", "code-review", "engineering"],
        "Measuring whether an AI reviewer actually improves code quality.",
        """We ran an AI code review assistant on all pull requests for three months and finally have data instead of opinions.

The numbers: it caught roughly one real issue per five PRs that humans missed — mostly edge cases, missing null checks, and inconsistent error handling. It also produced noise, about three comments per PR that were wrong or pedantic.

The unexpected effect: human reviewers started writing better first-pass reviews, apparently because the AI's comments raised the baseline of what gets discussed.

Net verdict: keep it, but tune it aggressively. The value is real but only after you tune out the noise. An unconfigured AI reviewer is a colleague who comments on everything.""",
    ),
    (
        2026,
        5,
        12,
        16,
        "Debugging in production: a field guide",
        ["debugging", "devops", "observability"],
        "Techniques for finding bugs that only reproduce in production.",
        """The bug only happens in production. Every engineer knows this special circle of debugging. A field guide from years of collecting these:

- Correlate, do not guess: traces plus logs plus the actual request payload beats theory every time
- Reproduce the conditions, not the bug: same data shape, same concurrency, same timing — the bug follows
- Feature flags are your laboratory: turn things off one at a time
- Write the fix as a test that would have caught it, or it will be back

And the meta-rule: production debugging is a systems skill, not a language skill. The person who knows where the logs live is worth more than the person who knows the algorithm.""",
    ),
    (
        2026,
        5,
        15,
        11,
        "Kotlin Multiplatform in production: the honest review",
        ["kotlin", "mobile", "cross-platform"],
        "Sharing business logic across iOS and Android with KMP after a year.",
        """We moved our core business logic — networking, caching, sync — to Kotlin Multiplatform a year ago. UI stayed native on both platforms. This split is the whole trick.

What works: one implementation of the hard logic, tested once, behaving identically on both platforms. Our platform-specific bug count dropped noticeably, and feature parity stopped being a negotiation.

What still hurts: iOS build integration requires Objective-C header wrangling that nobody enjoys, and the Swift interop for newer Kotlin features lags.

KMP is not a cross-platform UI framework, and judging it as one misses the point. As a logic-sharing layer, it is the most pragmatic option available.""",
    ),
    (
        2026,
        5,
        19,
        13,
        "Caching strategies ranked by how often they bite you",
        ["caching", "backend", "performance"],
        "From HTTP caching to distributed invalidation, ranked by operational risk.",
        """There are only two hard things in computer science, and caching is the one that pages you. A ranking of strategies by operational risk, learned the hard way:

1. HTTP caching with explicit TTLs — boring, predictable, lowest risk
2. Application-level memoization — safe as long as it is per-request
3. Redis with TTLs — fine until someone sets a TTL of a week
4. Write-through caches — fine until a write path is missed
5. Event-driven invalidation — powerful, and every missed event is a stale-forever bug

The universal rule: every cache needs an answer to "how does this get invalidated, and what happens when that fails?" If the answer is a shrug, you do not have a cache, you have a liability.""",
    ),
    (
        2026,
        5,
        22,
        9,
        "From side project to production: the checklist I wish I had",
        ["side-project", "devops", "process"],
        "Everything a hobby project needs before real people depend on it.",
        """A friend's side project got real users this month, so I wrote down everything I wish I had checked before my own projects had users.

The minimum production checklist:

- Backups that have actually been restored at least once
- Error tracking, not just logs — you will not find the errors by reading
- Uptime monitoring with alerts to your actual phone
- A rollback path for every deploy
- One page that says what this service is, what it depends on, and who to wake up

None of this is fun. All of it is cheaper than the first incident. The difference between a demo and a product is not features — it is whether you can fix it at 2am.""",
    ),
    (
        2026,
        5,
        26,
        15,
        "The hidden cost of ORMs: a query plan investigation",
        ["database", "orm", "performance"],
        "Tracing a production slowdown back to an innocent-looking ORM call.",
        """Our slowest endpoint had no obvious problem: one ORM call, a simple filter, an indexed column. The query plan told a different story — a sequential scan on a 40-million-row table.

Root cause: the ORM's expression wrapper prevented the index from being used, because the generated comparison cast the column to text. The fix was one line. Finding it took two days.

The lessons:

- ORM abstractions leak at the query planner, not the API
- Log the actual SQL in development, always
- `EXPLAIN ANALYZE` on your top ten queries belongs in your onboarding

I am not anti-ORM. I am anti-unknown-SQL. Know what your tools generate.""",
    ),
    (
        2026,
        5,
        29,
        10,
        "Choosing boring technology, again",
        ["architecture", "engineering-culture", "teams"],
        "A defense of boring technology after a year of exciting choices.",
        """We tried some exciting technology last year. This is a retrospective, not a confession — most of the experiments worked. But the accounting matters.

The exciting database saved us 30 percent on storage and cost us three weeks of operational learning. The exciting queue framework was elegant and its failure modes were not. The boring choices — Postgres, Redis, a queue that is just a table — never appeared in an incident review.

The math I now apply: every novel technology carries a hidden tax of unknown-unknowns, paid in the currency of your team's attention. Sometimes the tax is worth it. Usually it is not. Choose boring, spend the saved attention on the product.""",
    ),
    # ---- 2026-06 ----
    (
        2026,
        6,
        2,
        9,
        "WWDC 2026 recap: what I am actually adopting",
        ["ios", "swift", "wwdc"],
        "Cutting through the keynote to the changes that matter for shipping apps.",
        """WWDC week again. Behind the keynote polish, here is what will actually change how I work this year.

The new on-device model APIs are the headline for us — on-device inference with a real API means features that were cloud-only become private and free. I have a prototype running already.

Also adopting: the updated design language, incrementally, starting with our newest screens. Skipping for now: the platform-specific features for surfaces we do not ship on.

Standard advice: do not migrate your main branch in June. Branch, prototype, and let the betas shake out. The teams that ship in September are the ones that started measured in June.""",
    ),
    (
        2026,
        6,
        5,
        14,
        "Android at Google I/O 2026: the developer takeaway",
        ["android", "google", "mobile"],
        "The announcements from I/O that will change Android development work.",
        """Google I/O delivered its usual avalanche, and as always, the developer-relevant parts were a fraction of the keynote. The fraction that matters:

- The on-device AI APIs are now stable enough to build on, with sensible fallbacks for older devices
- Studio's AI-assisted refactoring works on real codebases now, not just samples — skeptical, then surprised
- The performance tooling got a unified view that finally connects jank to its cause

My plan, as every year: adopt the stable things this quarter, watch the previews, and let the community find the sharp edges before my users do.""",
    ),
    (
        2026,
        6,
        9,
        10,
        "Six months of AI pair programming: what stuck",
        ["ai", "productivity", "programming"],
        "An honest mid-year review of AI coding tools in daily work.",
        """Six months into using AI coding assistants daily, the novelty is gone and the real picture is clear.

What stuck: boilerplate elimination, test scaffolding, translating between languages, and explaining unfamiliar code. These are real, daily wins.

What did not stick: architecture decisions, security-sensitive code, and anything where the context lives in my head rather than the repository. The assistant does not know why we chose this design, and it confidently suggests the alternative we rejected.

The skill that emerged is knowing which tasks to hand over. Delegation, not automation. The engineers getting the most value are not the ones with the best prompts — they are the ones with the best judgment about what to delegate.""",
    ),
    (
        2026,
        6,
        12,
        16,
        "Load testing before the launch, not after the incident",
        ["performance", "testing", "reliability"],
        "A practical load testing setup that found our bottleneck before users did.",
        """Before our biggest launch of the year, we load tested — properly, for the first time. It found a connection pool exhaustion bug that would have taken us down in minute three of the launch. Best two days of work this quarter.

The setup that worked:

- Replay real traffic patterns from production logs, not synthetic uniform load
- Test at 3x expected peak, because estimates are estimates
- Watch the database, not just the app tier — the bottleneck is never where you think
- Practice the mitigation, not just the test: what exactly do you turn off first?

Load testing is a rehearsal. You are not proving the system works; you are learning how it fails, while it is still cheap to learn.""",
    ),
    (
        2026,
        6,
        16,
        11,
        "The mid-year stack review: what changed since January",
        ["retrospective", "engineering", "tools"],
        "Reviewing our technology choices at mid-year, with the benefit of data.",
        """Mid-year, so a stack review with actual data instead of vibes. What changed since January's planning:

Kept and happy: the modular monolith, Postgres-first architecture, and the eval pipeline for AI features. All three exceeded expectations.

Kept and mixed: the AI code reviewer (valuable after tuning, noisy before) and Rust for hot paths (right call, higher maintenance cost than hoped).

Reversed: one microservice split we undid in April, and a vector database we consolidated into Postgres in February.

The pattern in the reversals: we had adopted technology for the workload we imagined, not the workload we measured. The stack review exists to catch exactly that.""",
    ),
    (
        2026,
        6,
        19,
        13,
        "HTTP/3 in practice: enabling it and what broke",
        ["networking", "backend", "performance"],
        "Turning on HTTP/3 across our services and the surprises along the way.",
        """We enabled HTTP/3 across our public endpoints this month. The performance numbers were as advertised — noticeably better tail latency for mobile users on flaky networks. The surprises were elsewhere.

What broke or surprised:

- One corporate proxy environment in our user base silently downgraded; we kept TCP fallback obviously, but monitoring needed to distinguish the protocols
- Connection migration genuinely helps users switching between Wi-Fi and cellular — support tickets about "app freezing on network change" disappeared
- Load balancer configuration was where all the real time went

Worth doing, and easier than the last time I evaluated it. The mobile user experience improvement alone justifies it.""",
    ),
    (
        2026,
        6,
        23,
        9,
        "Documentation that engineers actually read",
        ["documentation", "engineering-culture", "teams"],
        "What we changed to make internal docs live instead of rot.",
        """Our internal documentation used to be a graveyard of onboarding pages last updated three years ago. A quarter of focused effort changed the culture, not just the pages.

What worked:

- Docs live next to the code they describe, in the same PR
- Every runbook gets exercised: if an incident used it, we fix the gaps immediately after
- We deleted ruthlessly — a wrong doc is worse than no doc, and stale docs are wrong docs
- "How do I test this locally?" is the first section of every service README, because it is the first question every engineer asks

The insight: documentation is not a writing problem, it is a workflow problem. Make updating docs the path of least resistance and they stop rotting.""",
    ),
    (
        2026,
        6,
        26,
        15,
        "Half a year of blogging: what writing taught me about engineering",
        ["writing", "career", "retrospective"],
        "Reflections on six months of consistent technical writing.",
        """This is my fiftieth post in six months, which seems like a good place to reflect on the practice.

What I learned: writing is debugging for understanding. Half the time I sat down to explain something I understood, I discovered I understood the shape of it, not the substance. The posts I am proudest of are the ones where the writing changed my own conclusion.

What surprised me: the audience effect on quality. Knowing someone might read this made me test the code examples, question my claims, and delete my hedges. Writing in public is peer review with a faster feedback loop.

The habit matters more than any single post. Write the next one.""",
    ),
]


def main() -> None:
    created = 0
    for year, month, day, hour, title, tags, description, content in POSTS:
        payload = {
            "author": AUTHOR,
            "title": title,
            "content": content,
            "tags": tags,
            "meta": {
                "category": "tech",
                "description": description,
                "language": "en",
                "keywords": tags,
                "title": title,
            },
            "publishedAt": f"{year:04d}-{month:02d}-{day:02d}T{hour:02d}:00:00+00:00",
        }
        req = urllib.request.Request(
            BASE,
            data=json.dumps(payload).encode(),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {TOKEN}",
            },
            method="POST",
        )
        for attempt in range(10):
            try:
                with urllib.request.urlopen(req) as resp:
                    if resp.status == 201:
                        created += 1
                        print(f"created: {title}")
                    else:
                        print(f"unexpected status {resp.status}: {title}")
                break
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    wait = 10 * (attempt + 1)
                    print(f"rate limited on '{title}', waiting {wait}s...")
                    time.sleep(wait)
                    req = urllib.request.Request(
                        BASE,
                        data=json.dumps(payload).encode(),
                        headers={
                            "Content-Type": "application/json",
                            "Authorization": f"Bearer {TOKEN}",
                        },
                        method="POST",
                    )
                else:
                    print(f"FAILED ({e.code}): {title} — {e.read().decode()[:200]}")
                    break
    print(f"\n{created}/{len(POSTS)} posts created")


if __name__ == "__main__":
    main()
