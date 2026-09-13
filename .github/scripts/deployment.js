// Record a GitHub Deployment for a Pages directory, so the pull request
// shows "View deployment", the repository's Deployments sidebar lists what
// is live where, and each environment keeps its history. Used with
// actions/github-script:
//
//   record({github, context, core}, {environment, task, url, ref, production})
//   retire({github, context, core}, {environment, task})
//
// The token needs deployments: write. Creating a deployment for an
// environment creates the environment; no protection rules apply to it.
//
// Environments are long-lived: production (the site root), main, and one
// shared preview for every pull request. A pull request does not get an
// environment of its own because the workflow token cannot delete
// environments (DELETE /environments needs repository administration), so
// per-pull-request environments would outlive their pull requests. What a
// pull request owns is its deployments, identified by task = "preview/pr-N",
// and those the token can inactivate and delete.
module.exports = {
  async record({ github, context, core }, { environment, task = "deploy", url, ref, production = false }) {
    const { owner, repo } = context.repo;
    // Earlier deployments of the same task are superseded: inactive, then
    // gone, so the sidebar shows one entry per pull request, not one per
    // push. auto_inactive is off because in the shared preview environment
    // it would retire other pull requests' live deployments.
    await module.exports.retire({ github, context, core }, { environment, task, quiet: true });
    const deployment = await github.rest.repos.createDeployment({
      owner, repo, ref, environment, task,
      auto_merge: false,
      required_contexts: [],
      transient_environment: false,
      production_environment: production,
      description: `${task} at ${url}`,
    });
    if (deployment.status !== 201) {
      core.setFailed(`deployment not created: ${JSON.stringify(deployment.data)}`);
      return;
    }
    await github.rest.repos.createDeploymentStatus({
      owner, repo,
      deployment_id: deployment.data.id,
      state: "success",
      environment_url: url,
      log_url: `${context.serverUrl}/${owner}/${repo}/actions/runs/${context.runId}`,
      auto_inactive: false,
    });
    core.info(`deployed ${environment} (${task}): ${url}`);
  },

  async retire({ github, context, core }, { environment, task, quiet = false }) {
    const { owner, repo } = context.repo;
    const deployments = await github.paginate(github.rest.repos.listDeployments, {
      owner, repo, environment, task, per_page: 100,
    });
    for (const d of deployments) {
      await github.rest.repos.createDeploymentStatus({
        owner, repo, deployment_id: d.id, state: "inactive",
      });
      await github.rest.repos.deleteDeployment({ owner, repo, deployment_id: d.id });
    }
    if (!quiet || deployments.length) core.info(`retired ${deployments.length} deployment(s) of ${task} in ${environment}`);
  },
};
