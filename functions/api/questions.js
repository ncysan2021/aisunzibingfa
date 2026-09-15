// GET /api/questions
// 随机抽 10 题，只返回题目和选项，绝不返回 answer / explanation。
export async function onRequestGet({ env }) {
  try {
    const { results } = await env.DB.prepare(
      `SELECT id, topic, question,
              option_a, option_b, option_c, option_d
         FROM questions
     ORDER BY RANDOM()
        LIMIT 10`
    ).all();

    return new Response(JSON.stringify({ questions: results }), {
      headers: {
        "Content-Type": "application/json; charset=utf-8",
        "Cache-Control": "no-store",
      },
    });
  } catch (err) {
    return new Response(
      JSON.stringify({ error: "DB query failed", detail: String(err) }),
      {
        status: 500,
        headers: { "Content-Type": "application/json; charset=utf-8" },
      }
    );
  }
}