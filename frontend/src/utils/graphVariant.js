/**
 * 与 MainView 一致的「未消歧 / 已消歧」Tab 持久键与 graph_id 解析。
 */

export function resolveProjectGraphId(project, variant) {
  if (!project) return null
  if (
    project.graph_id_raw &&
    project.graph_id_disamb &&
    project.graph_id_raw !== project.graph_id_disamb &&
    variant === 'raw'
  ) {
    return project.graph_id_raw
  }
  return project.graph_id_disamb || project.graph_id
}

export function getGraphVariantForProject(projectId) {
  if (!projectId) return 'disamb'
  return localStorage.getItem(`mirofish_gv_${projectId}`) === 'raw' ? 'raw' : 'disamb'
}

export function effectiveGraphIdFromProject(project, projectId) {
  return resolveProjectGraphId(project, getGraphVariantForProject(projectId))
}
