// 实体消歧三组实验数据 — 由 Home.vue 内嵌 showcase 与 DemoView.vue 完整页共用
// 数据来源：实际跑过的三个项目的 graph_quality 评测结果
export const tasks = [
  {
    index: 1,
    model: 'qwen3-max-preview',
    nodeReductionRatio: 0.688312,
    pairDecisions: 6,
    mergedGroups: 0,
    merges: [],
    raw:    { nodes: 77, edges: 70,  isolatedRatio: 0.25974,  avgDegree: 1.8182,  duplicateGroups: 4 },
    disamb: { nodes: 24, edges: 121, isolatedRatio: 0.041667, avgDegree: 10.083,  duplicateGroups: 0 },
  },
  {
    index: 2,
    model: 'qwen3-coder-flash',
    nodeReductionRatio: 0.488372,
    pairDecisions: 9,
    mergedGroups: 1,
    merges: [
      { canonical: '吴泽明', removed: ['范禹'], kept: '7e0411f1', label: 'Person' },
    ],
    raw:    { nodes: 43, edges: 52, isolatedRatio: 0.046512, avgDegree: 2.4186, duplicateGroups: 2 },
    disamb: { nodes: 22, edges: 45, isolatedRatio: 0.0,      avgDegree: 4.0909, duplicateGroups: 0 },
  },
  {
    index: 3,
    model: 'qwen3-coder-flash',
    nodeReductionRatio: 0.388889,
    pairDecisions: 2,
    mergedGroups: 0,
    merges: [],
    raw:    { nodes: 18, edges: 21, isolatedRatio: 0.111111, avgDegree: 2.3333, duplicateGroups: 1 },
    disamb: { nodes: 11, edges: 13, isolatedRatio: 0.0,      avgDegree: 2.3636, duplicateGroups: 0 },
  },
]

// 全局聚合统计（4 个 hero stat 卡片用）
export const summary = {
  taskCount: 3,
  pairDecisionsTotal: 17,
  avgNodeCompressionPercent: 52,
  duplicateEliminationRate: 100,
}
