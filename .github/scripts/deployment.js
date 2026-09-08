// Record a GitHub Deployment for a Pages directory, so the pull request
// shows "View deployment", the repository's Deployments sidebar lists what
// is live where, and each environment keeps its history. Used with
// actions/github-script:
//
//   record({github, context, core}, {environment, url, ref, production, transient})
//   retire({github, context, core}, {environment})   // close: inactive + gone
//
// The token needs deployments: write. Creating a deployment for an
// environment creates the environment; no protection rules apply to it.
module.exports = {
  async record({ github, context, core }, { environment, url, ref, production = false, transient = false }) {
    const { owner, repo } = context.repo;
    const deployment = await github.rest.repos.createDeployment({
      owner, repo, ref, environment,
      auto_merge: false,
      required_contexts: [],
      transient_environment: transient,
      production_environment: production,
      description: `${environment} at ${url}`,
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
      auto_inactive: true,   // earlier deployments of this environment are superseded
    });
    core.info(`deployed ${environment}: ${url}`);
  },

  async retire({ github, context, core }, { environment }) {
    const { owner, repo } = context.repo;
    const deployments = await github.rest.repos.listDeployments({ owner, repo, environment, per_page: 100 });
    for (const d of deployments.data) {
      await github.rest.repos.createDeploymentStatus({
        owner, repo, deployment_id: d.id, state: "inactive",
      });
    }
    try {
      await github.rest.repos.deleteAnEnvironment({ owner, repo, environment_name: environment });
      core.info(`removed environment ${environment}`);
    } catch (error) {
      core.info(`environment ${environment} not removed: ${error.message}`);
    }
  },
};
