# PawPal+ Project Reflection

## 1. System Design

**a. Initial design**

I sketched the whole thing in UML before writing any code. The idea was to keep
two worlds separate: the "stuff" (an owner who has pets, pets that have care
tasks) and the "brain" (a scheduler that takes all the tasks plus the day's
constraints and turns them into a plan).

So the classes ended up being:

- Owner — the user. Knows their pets and their preferences, like when the day
  starts and ends and how much free time they actually have.
- Pet — name, species, and its own list of tasks.
- Task — one care item. What it is, how long it takes, how important it is,
  and optionally a fixed time (like a vet appointment) or a repeat schedule
  (daily/weekly).
- Scheduler — the brain. Doesn't store anything; it takes tasks and
  constraints and hands back a plan.
- DailyPlan and ScheduledTask — the output. Each slot in the plan remembers
  why it got placed where it did, and anything that got cut keeps a reason too.

The one rule I stuck to the whole time: none of the logic touches Streamlit.
The app file just collects input and shows results, which meant everything
important could be tested from the terminal.

**b. Design changes**

A lot changed once I actually started building.

While implementing:

- Time became plain integers (minutes from midnight) instead of datetime
  objects. Python's time type can't do math, and "480 + 30" is a lot easier to
  test than juggling datetimes. Converting to "08:00" only happens right
  before something gets displayed.
- Priorities became comparable numbers so sorting by importance just works.
- The scheduler went stateless. Originally it stored its own constraints, but
  passing them in each time turned out cleaner, especially with Streamlit
  re-running the whole script on every click.
- I split the owner's preferences from the scheduler's constraints, so the
  brain never needs to know anything about the UI side.

Then I had an AI review pass over the finished module, and it turned out the
design was kind of half-wired: a bunch of fields existed that nothing actually
read. Fixed appointment times weren't being honored (everything just got
packed back to back), the per-slot reasoning was being computed and then
thrown away, and a couple of helpers were written and tested but never called.
I wired all of that up. I also deliberately ignored some of its suggestions —
more on that in section 3.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

The scheduler cares about: how much free time the owner actually has (which
can be way less than the day itself), when the day starts and ends, task
priority, duration, fixed appointment times, an optional cap on how many tasks
to schedule, and whether a task is already done or not due yet.

Time budget and priority mattered most, and that came straight from the
scenario. A busy owner's real question is "I've got two free hours, what's
most important?" If the scheduler gets those two things wrong, nothing else
about it matters.

**b. Tradeoffs**

Tradeoff 1: conflict detection gives one warning per affected task, not every
possible pair. My first version only compared neighbors after sorting by time,
and an AI review found a real miss there — a long task can overlap something
two spots down the list, not just the next one. I switched to a sweep that
tracks whichever window runs the longest, which catches those. It still won't
list every single colliding pair in a big pileup, but for a warning meant for
a human, one clear message per affected task is honestly more useful than an
exhaustive list.

Tradeoff 2: greedy scheduling instead of optimal packing. When time is tight,
the scheduler fills leftover gaps with whatever still fits, so a short
low-priority task can make the cut while a long high-priority one gets
dropped. A smarter packing algorithm exists, but greedy gets more tasks done,
runs instantly, and is easy to explain — which fits a pet care app better than
squeezing out mathematically optimal minutes.

---

## 3. AI Collaboration

**a. How you used AI**

I used my AI assistant the whole way through: drafting the UML, generating the
class skeletons, writing tests before the implementation existed, and
reviewing the finished code. The single most useful trick was fresh sessions —
spinning up a separate chat that hadn't watched me build anything and having
it plan or review cold. That's how the half-wired fields got caught, and later
how a real bug in the conflict detection got found.

Specific, slightly hostile prompts worked best: "what's declared here that
nothing uses," "find an input where this gives a wrong answer," "is the bug in
my test or in my logic." Generic "review my code" prompts got generic answers.

Keeping different phases in different chats helped more than I expected. A
session that only saw the files couldn't just nod along with decisions it had
watched me make, and it kept planning conversations from bleeding into
implementation ones.

**b. Judgment and verification**

One rejection and one acceptance, because both matter.

Rejected: a review suggested making task selection strictly priority-ordered —
once a high-priority task gets skipped, stop filling the gaps with smaller
stuff. I kept the greedy version on purpose. Doing four small tasks beats
doing two big ones for a pet owner, so I wrote it down as a tradeoff instead
of changing code.

Accepted: when I asked for a simplification of my conflict checker, the AI
claimed my version missed long tasks that span multiple later ones. I didn't
just take its word — I wrote that exact three-task scenario as a test, watched
my version genuinely fail it, and then switched. That became the house rule:
if the AI says "bug," it has to show up as a failing test before any code
changes.

---

## 4. Testing and Verification

**a. What you tested**

89 tests. The big buckets: sorting comes out right and is deterministic
(including ties), the time budget never gets blown and skipped tasks always
say why, slots never overlap and stay inside the day, fixed appointments land
where they should, recurring tasks spawn the right next occurrence without
duplicating themselves, conflicts get flagged instead of crashing, and a bunch
of weird inputs — empty list, zero free minutes, a day that ends before it
starts, everything already done.

Most of the tests were written before the logic existed, so they basically
were the spec. Done meant green, not "looks right." That approach caught a
real bug at the very end: finishing a daily task was putting tomorrow's copy
straight back into today's plan.

**b. Confidence**

Around 4 out of 5. The core is well covered and the demo script runs
everything end to end. With more time I'd test: duplicate task ids coming from
the UI (two tasks named "Walk" currently collide), fixed appointments losing
their spot to the task-count cap, and the Streamlit layer itself, which only
has a smoke check.

---

## 5. Reflection

**a. What went well**

The logic/UI split. Since all the brains live in one plain Python file, I
could test everything from the terminal, and hooking up the UI at the end was
mostly plumbing. The explanation feature also came out better than planned —
every slot and every skipped task says why, which turned out to be great for
debugging too, not just for the user.

**b. What you would improve**

The id scheme for recurring tasks grows forever (the date gets glued on every
time one completes), and tasks created from the UI fall back to using their
title as an id, so two tasks with the same name collide. Both small, both the
kind of thing that bites later. I'd also protect fixed appointments from the
task cap — a vet visit shouldn't lose its spot to something minor that
happened to sort first.

**c. Key takeaway**

Being the "lead architect" mostly meant deciding what not to accept. The AI
was legitimately good — it generated solid code, found dead weight, and caught
a correctness bug I'd missed — but it would also happily suggest changes that
were technically better and wrong for this project. The setup that worked: I
make the design calls and write them down, fresh sessions attack the work
cold, and any claimed bug has to reproduce as a failing test before code
changes. The tests ended up being the contract that kept both of us honest.
