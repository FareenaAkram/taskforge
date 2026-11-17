(function () {
  "use strict";
  var data = window.TASKFORGE;
  var $ = function (id) { return document.getElementById(id); };

  // Small DOM helper: never uses innerHTML, so dataset text cannot inject markup.
  function h(tag, attrs) {
    var el = document.createElement(tag);
    Object.keys(attrs || {}).forEach(function (k) {
      if (k === "class") el.className = attrs[k];
      else if (k === "text") el.textContent = attrs[k];
      else el.setAttribute(k, attrs[k]);
    });
    (function add(list) {
      list.forEach(function (c) {
        if (c == null) return;
        if (Array.isArray(c)) return add(c);
        el.appendChild(typeof c === "string" ? document.createTextNode(c) : c);
      });
    })(Array.prototype.slice.call(arguments, 2));
    return el;
  }
  function pretty(s) { return s.replace(/_/g, " "); }

  if (!data) {
    $("detail").textContent = "data.js not found. Run: python -m taskforge build";
    return;
  }
  var stats = data.stats, tasks = data.tasks;

  // ---- header + tiles
  var m = stats.meta, t = stats.totals;
  $("meta").textContent = "v" + m.version + " · generated " + m.generated_at + " · Python " + m.python + " · pytest " + m.pytest + " · seed " + m.seed;
  [
    [t.tasks, "verified tasks"],
    [t.repos, "source repos"],
    [Math.round(t.mutation_score * 100) + "%", "mean test mutation score"],
    [t.avg_fail_to_pass, "avg fail-to-pass tests"],
    [t.avg_pass_to_pass, "avg regression tests"],
    [Math.round(t.alternative_fix_rate * 100) + "%", "tasks with an alternative valid fix"]
  ].forEach(function (x) { $("tiles").appendChild(h("div", { "class": "tile" }, h("b", { text: String(x[0]) }), h("span", { text: x[1] }))); });

  // ---- bars
  function bars(el, rows, max, cls) {
    rows.forEach(function (r) {
      var pct = max ? Math.max(0, (r.count / max) * 100) : 0;
      var fill = h("div", { "class": "fill" });
      fill.style.width = pct + "%";
      el.appendChild(h("div", { "class": "bar " + (r.cls || cls || "") },
        h("div", { "class": "label", text: r.label }),
        h("div", { "class": "track" }, fill),
        h("div", { "class": "num", text: String(r.count) })));
    });
  }
  var funnelMax = Math.max.apply(null, stats.funnel.map(function (f) { return f.count; }));
  bars($("funnel"), stats.funnel.filter(function (f) { return f.count > 0 || f.key === "accepted"; }).map(function (f) {
    var cls = f.key === "accepted" ? "accept" : /^(survived|timeout|collection_error|too_broad|flaky|patch_roundtrip|golden_fails|leaky_issue)$/.test(f.key) ? "reject" : /^(duplicate_signature|not_sampled)$/.test(f.key) ? "drop" : "";
    return { label: f.label, count: f.count, cls: cls };
  }), funnelMax);
  var order = ["easy", "medium", "hard"];
  var dMax = Math.max.apply(null, order.map(function (k) { return stats.difficulty[k] || 0; }));
  bars($("difficulty"), order.map(function (k) { return { label: k, count: stats.difficulty[k] || 0 }; }), dMax);
  var kinds = Object.keys(stats.kinds).sort(function (a, b) { return stats.kinds[b] - stats.kinds[a]; });
  bars($("kinds"), kinds.map(function (k) { return { label: pretty(k), count: stats.kinds[k] }; }), stats.kinds[kinds[0]]);

  // ---- repo table
  var tbl = $("repos");
  tbl.appendChild(h("thead", {}, h("tr", {}, ["Repo", "LOC", "Tests", "Mutants", "Mutation score", "Tasks"].map(function (x) { return h("th", { text: x }); }))));
  var tb = h("tbody");
  stats.repos.forEach(function (r) {
    var mini = h("span", { "class": "mini" }, h("i", { style: "width:" + Math.round(r.mutation_score * 100) + "%" }));
    tb.appendChild(h("tr", {}, h("td", {}, h("code", { text: r.name })), h("td", { text: String(r.loc) }), h("td", { text: String(r.tests) }),
      h("td", { text: String(r.mutants) }), h("td", {}, mini, Math.round(r.mutation_score * 100) + "%"), h("td", { text: String(r.tasks) })));
  });
  tbl.appendChild(tb);

  // ---- explorer
  var state = { repo: "", kind: "", tier: "", q: "", selected: tasks.length ? tasks[0].instance_id : null };
  function option(sel, value, label) { sel.appendChild(h("option", { value: value, text: label })); }
  var fr = $("f-repo"), fk = $("f-kind");
  option(fr, "", "All repos");
  stats.repos.forEach(function (r) { option(fr, r.name, r.name); });
  option(fk, "", "All bug types");
  kinds.forEach(function (k) { option(fk, k, pretty(k)); });
  ["", "easy", "medium", "hard"].forEach(function (tier) {
    var b = h("button", { type: "button", "class": "chip", "aria-pressed": String(tier === state.tier), text: tier || "all" });
    b.addEventListener("click", function () {
      state.tier = tier;
      Array.prototype.forEach.call($("f-tier").children, function (c) { c.setAttribute("aria-pressed", String(c === b)); });
      render();
    });
    $("f-tier").appendChild(b);
  });
  fr.addEventListener("change", function () { state.repo = fr.value; render(); });
  fk.addEventListener("change", function () { state.kind = fk.value; render(); });
  $("f-q").addEventListener("input", function (e) { state.q = e.target.value.toLowerCase(); render(); });

  function matches(task) {
    if (state.repo && task.repo !== state.repo) return false;
    if (state.kind && task.mutation_kinds.indexOf(state.kind) < 0) return false;
    if (state.tier && task.difficulty.tier !== state.tier) return false;
    if (state.q) {
      var hay = (task.problem_statement + " " + task.fail_to_pass.join(" ")).toLowerCase();
      if (hay.indexOf(state.q) < 0) return false;
    }
    return true;
  }
  function summary(task) {
    var first = task.problem_statement.split("\n")[0].replace(/^##\s*/, "");
    return first.replace(/^`[^`]+`:\s*/, "");
  }
  function renderList(visible) {
    var ul = $("list");
    ul.textContent = "";
    visible.forEach(function (task) {
      var b = h("button", { type: "button", "aria-current": String(task.instance_id === state.selected) },
        h("span", { "class": "id", text: task.instance_id }),
        h("span", { "class": "badge " + task.difficulty.tier, text: task.difficulty.tier }),
        task.bug_count > 1 ? h("span", { "class": "badge", text: task.bug_count + " bugs" }) : null,
        h("span", { "class": "sum", text: summary(task) }));
      b.addEventListener("click", function () { state.selected = task.instance_id; render(); });
      ul.appendChild(h("li", {}, b));
    });
  }
  function diffBlock(patch) {
    var pre = h("pre", { "class": "diff" });
    patch.split("\n").forEach(function (line) {
      if (!line) return;
      var cls = line.indexOf("@@") === 0 ? "hunk" : /^(---|\+\+\+)/.test(line) ? "ctx" : line[0] === "+" ? "add" : line[0] === "-" ? "del" : "ctx";
      pre.appendChild(h("span", { "class": cls, text: line }));
    });
    return pre;
  }
  function testList(cls, items) {
    var ul = h("ul");
    items.forEach(function (x) { ul.appendChild(h("li", { text: x.replace(/^test_[a-z]+\.py::/, "") })); });
    return h("div", { "class": cls }, ul);
  }
  function renderDetail(task) {
    var d = $("detail");
    d.textContent = "";
    if (!task) { d.appendChild(h("p", { "class": "empty", text: "No task matches these filters." })); return; }
    d.appendChild(h("h3", { text: task.instance_id }));
    d.appendChild(h("p", { "class": "kv" },
      h("span", {}, "difficulty ", h("b", { text: task.difficulty.tier })),
      h("span", {}, "solver trials ", h("b", { text: (task.difficulty.solved ? "" : ">") + task.difficulty.attempts })),
      h("span", {}, "bugs ", h("b", { text: String(task.bug_count) })),
      h("span", {}, "type ", h("b", { text: task.mutation_kinds.map(pretty).join(" + ") })),
      h("span", {}, "patch lines ", h("b", { text: String(task.quality.changed_lines) }))));
    d.appendChild(h("h4", { text: "Problem statement" }));
    d.appendChild(h("pre", { "class": "stmt", text: task.problem_statement }));
    d.appendChild(h("h4", { text: "Golden patch" }));
    d.appendChild(diffBlock(task.patch));
    d.appendChild(h("h4", { text: "Tests (" + task.fail_to_pass.length + " fail-to-pass · " + task.pass_to_pass.length + " pass-to-pass)" }));
    d.appendChild(h("div", { "class": "tests" }, testList("f2p", task.fail_to_pass), testList("p2p", task.pass_to_pass)));
    d.appendChild(h("h4", { text: "Checks this task passed" }));
    d.appendChild(h("div", { "class": "checks" },
      h("div", { text: "Fails on the buggy snapshot, identical in " + task.validation.buggy_runs + " runs (not flaky)" }),
      h("div", { text: "Golden patch applies cleanly (context verified) and restores the original source" }),
      h("div", { text: "All " + task.validation.tests_total + " tests pass after the patch" }),
      h("div", { text: "Problem statement does not contain any line of the fix" }),
      h("div", { text: task.quality.alternative_fix_found ? "Note: the solver found a different valid fix (tests admit more than one solution)" : "Solver's fix, when found, matched the golden patch" })));
  }
  function render() {
    var visible = tasks.filter(matches);
    if (!visible.some(function (x) { return x.instance_id === state.selected; })) state.selected = visible.length ? visible[0].instance_id : null;
    $("count").textContent = visible.length + " of " + tasks.length + " tasks";
    renderList(visible);
    renderDetail(visible.filter(function (x) { return x.instance_id === state.selected; })[0]);
  }
  render();
})();
