// POST /api/submit
// 请求体：{ "answers": [ { "id": 1, "choice": "A" }, ... ] }
// 响应体：{ score, total, results: [ { id, question, option_a..d, your, correct, is_correct, explanation }, ... ] }
export async function onRequestPost({ request, env }) {
  // 1. 解析 JSON
  let body;
  try {
    body = await request.json();
  } catch {
    return jsonError(400, "请求体不是合法 JSON");
  }

  const answers = body && body.answers;
  if (!Array.isArray(answers) || answers.length === 0 || answers.length > 50) {
    return jsonError(400, "answers 必须是非空数组，长度不超过 50");
  }

  // 2. 校验每一项
  const ids = [];
  const userChoices = {};
  for (const item of answers) {
    if (!item || typeof item !== "object") {
      return jsonError(400, "answers 里存在非对象元素");
    }
    const id = Number(item.id);
    const choice = String(item.choice || "").toUpperCase();

    if (!Number.isInteger(id) || id <= 0) {
      return jsonError(400, "id 必须是正整数");
    }
    if (!["A", "B", "C", "D"].includes(choice)) {
      return jsonError(400, "choice 必须是 A/B/C/D");
    }
    if (userChoices[id] !== undefined) {
      return jsonError(400, `id ${id} 重复`);
    }
    ids.push(id);
    userChoices[id] = choice;
  }

  // 3. 从 D1 查正确答案（参数化，防注入）
  const placeholders = ids.map(() => "?").join(",");
  const stmt = env.DB.prepare(
    `SELECT id, question,
            option_a, option_b, option_c, option_d,
            answer, explanation
       FROM questions
      WHERE id IN (${placeholders})`
  ).bind(...ids);

  let results;
  try {
    ({ results } = await stmt.all());
  } catch (err) {
    return new Response(
      JSON.stringify({ error: "DB query failed", detail: String(err) }),
      {
        status: 500,
        headers: { "Content-Type": "application/json; charset=utf-8" },
      }
    );
  }

  // 4. 判分，按用户提交顺序输出
  const byId = new Map(results.map((r) => [r.id, r]));
  let score = 0;
  const details = [];

  for (const id of ids) {
    const q = byId.get(id);
    if (!q) continue; // 题库里没这个 id，跳过
    const your = userChoices[id];
    const correct = q.answer;
    const isCorrect = your === correct;
    if (isCorrect) score += 1;
    details.push({
      id: q.id,
      question: q.question,
      option_a: q.option_a,
      option_b: q.option_b,
      option_c: q.option_c,
      option_d: q.option_d,
      your,
      correct,
      is_correct: isCorrect,
      explanation: q.explanation,
    });
  }

  return new Response(
    JSON.stringify({
      score,
      total: details.length,
      results: details,
    }),
    {
      headers: {
        "Content-Type": "application/json; charset=utf-8",
        "Cache-Control": "no-store",
      },
    }
  );
}

function jsonError(status, message) {
  return new Response(JSON.stringify({ error: message }), {
    status,
    headers: { "Content-Type": "application/json; charset=utf-8" },
  });
}