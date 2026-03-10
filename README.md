# What?
Deploy full VEDA stack easily.

# How to deploy?
## Steps
1. Create a new Github Environment in the repository. See [Requirements](#requirements) on details of creating the environment.
2. Add necessary env vars in the Environment
3. Go to Actions. Select "Dispatch" workflow. Select "Run workflow", choose the environment from step 1. Select the components to dispatch and then "Run workflow."
4. (Optional) To add a new component in veda-deploy see [Add New Components](#add-new-components).

# Requirements

Adding new deployment environments requires admin permissions for this veda-deploy repository. New environments are added by entering project settings and selecting `Environments` from the code and automation menu. The environment naming convention is `<aws-account>-<stage>`, i.e. `smce-staging`. As more environments are added, this convention will need to be updated.

## GitHub Environment
Each veda-deploy Github Environment needs Environment Secrets and Variables configured in the GitHub UI Settings for this veda-deploy project as well as detailed key-value AWS Secrets Manager secret(s) with configuration for the deployment of all components.

### GitHub Environment Secrets
GitHub Environment secret(s) configured in the GitHub UI settings for this veda-deploy repo:
`DEPLOYMENT_ROLE_ARN` - oidc role with permissions to deploy

### GitHub Environment Variables
GitHub Environment variables need to be set in the GitHub UI project settings. There should be one variable for each AWS Secrets Manager secret name. There should be one variable for each component indicating which GitHub reference to use to deploy that component via checking out that Github reference in the git submodule.

More instructions on these Github environment variables is provided below.

#### AWS Secrets Manager Secret Name(s)

`DEPLOYMENT_ENV_SECRET_NAME` - the AWS secrets manager secret name with the required component env vars. See [AWS Secrets Requirements](#aws-secrets-requirements) for what env vars are needed. Note that the individual submodule GitHub repositories should be consulted for the most up to date environment variable names and explanations.

`SM2A_ENVS_DEPLOYMENT_SECRET_NAME` - the AWS secrets manager secret name with env vars specific to a SM2A deployment. See [AWS Secrets Requirements for SM2A](#aws-secrets-requirements-for-sm2a) for what env vars are needed.

#### GitHub References

Git Ref for each project to use to deploy. Can be branch name, release tag or commit hash. Anything that works with `git checkout`. Below are some examples of the components that may be configured in a GitHub Environment.

```bash
VEDA_AUTH_GIT_REF=<target branch name or tag default to main>
VEDA_BACKEND_GIT_REF=<target branch name or tag default to main>
VEDA_FEATURES_API_GIT_REF=<target branch name or tag default to main>
VEDA_SM2A_DATA_AIRFLOW_GIT_REF=<target branch name or tag default to main>
```
#### AWS Secrets Requirements
A single secret is used to store the configuration for all components for a given GitHub Environment. In some cases, an additional secret may be needed if a component does not have uniquely namespaced `.env` parameters and requires custom values--for example, the Self Managed Apache Airflow (SM2A) component requires a separate [SM2A secret](#aws-secrets-requirements-for-sm2a) in the AWS Secrets Manager.

```bash
AWS_ACCOUNT_ID=******
AWS_REGION=******
VPC_ID=******
SUBNET_TAGNAME=******
PERMISSIONS_BOUNDARY_POLICY_NAME=******
COGNITO_GROUPS=******
VEDA_DB_PGSTAC_VERSION=******
VEDA_DB_SCHEMA_VERSION=******
PREFIX=******
STATE_BUCKET_NAME=******
STATE_BUCKET_KEY=*****
STATE_DYNAMO_TABLE=*****
VEDA_STAC_PATH_PREFIX=*****
VEDA_RASTER_PATH_PREFIX=*****
```

#### AWS Secrets Requirements for SM2A
```bash
AIRFLOW_UID=******
PREFIX=******
VPC_ID=******
STATE_BUCKET_NAME=******
STATE_BUCKET_KEY=******
STATE_DYNAMO_TABLE=******
PRIVATE_SUBNETS_TAGNAME=******
PUBLIC_SUBNETS_TAGNAME=******
AIRFLOW_FERNET_KEY=******
AIRFLOW_DB_NAME=******
AIRFLOW_DB_USERNAME=******
AIRFLOW_DB_PASSWORD=******
PERMISSION_BOUNDARIES_ARN=******
DOMAIN_NAME=******
STAGE=******
TF_VAR_gh_app_client_id=******
TF_VAR_gh_app_client_secret=******
TF_VAR_gh_team_name=******
TF_VAR_subdomain=******
```



# Add New Components
> [!IMPORTANT]
> This section is intended to add a new component to an existing configured environment, see [How to Deploy](#how-to-deploy) to start from scratch. Please read the full overview before starting; some steps overlap.

## Overview
- [Add deployment action to component github repository](#add-deployment-action-to-component-github-repository)

- [Store `.env` configuration in AWS Secrets Manager](#store-env-configuration-in-aws-secrets-manager)

- [Add component submodule to veda-deploy](#add-component-submodule-to-veda-deploy)

- [Extend composite dispatched deployment action with an optional component job that uses the component submodule and environment secret](#extend-composite-dispatched-deployment-action)

- [Add new component release version and environment secret name to veda-deploy environment(s)](#add-new-component-release-version-and-environment-secret-name-to-veda-deploy-environments)

- [Configure domain and custom routes](#configure-domain-and-custom-routes)

## Add deployment action to component github repository
Dispatches from veda-deploy are composed of deployment actions imported from the component projects' repository, after it has been installed as [git submodule](https://git-scm.com/book/en/v2/Git-Tools-Submodules). The management of all configuration, testing, and deployment concerns is managed within the component's GitHub repository (not in veda-deploy).

Create a new `cdk-deploy/action.yml` in the component project's repository. On a dispatch, the configured release version of the project will be checked out and executed on the veda-deploy GitHub runner. 

To keep the components modular, each action should include all necessary steps for deployment including Python and Node setup steps. While veda-deploy uses the same runner to deploy all components, it should not be assumed that the runner already has all needed installations and environment configuration from other components (unless a dependency is configured for the job using needs: {upstream-job-name}).

> [!TIP]
> Most deployments require [custom environment configuration](#store-env-configuration-in-aws-secrets-manager) that can be retrieved from the AWS Secrets Manager for the deployment. See [veda-backend/scripts/get-env.sh](https://github.com/NASA-IMPACT/veda-backend/blob/develop/scripts/get-env.sh) for an example environment configuration utility.

### Examples
- Veda-keycloak [grss-veda-keycloak](https://github.com/ieee-grss-veda/grss-veda-keycloak) provides Keycloak-based authentication with CDK deployment and post-deployment configuration via Lambda.
- Veda-backend [cdk-deploy/action.yml](https://github.com/NASA-IMPACT/veda-backend/blob/develop/.github/actions/cdk-deploy/action.yml) contains logic to run tests before deploying components.
- This [CICD workflow in veda-backend](https://github.com/NASA-IMPACT/veda-backend/blob/develop/.github/workflows/cicd.yml) demonstrates importing the cdk-deploy/action on a merge event to test the deployment in a dev enviornment.

## Store `.env` configuration in AWS Secrets Manager
AWS environment specific configuration like VPC ID and a Permission Boundary Policy Name are already included in a core key-value secret that can be loaded into the GitHub runner environment by your action. This core secret is set in the GitHub Variable `DEPLOYMENT_ENV_SECRET_NAME` (See [AWS Secrets Requirements](#aws-secrets-requirements) for the core variable names). Additional required configuration variables should be added to this core secret as needed for the new component. If your component requires custom configuration that conflicts with the core secret, a new secret can be configured--see the implementation of a custom secret for [SM2A](#aws-secrets-requirements-for-sm2a).

> [!NOTE]
> 1. For higher security environments, a permissions boundary policy needs to be identified. 
> 2. The qualifier of the CDK Toolkit bootstrapped for the target environment must be provided if not using the default toolkit.

## Add component submodule to veda-deploy
Add your component submodule to [.gitmodules](https://github.com/NASA-IMPACT/veda-deploy/blob/dev/.gitmodules). Submodules are checked out on the GitHub runner when your component is deployed.

```
[submodule "my-project"]
	path = my-project
	url = git@github.com:NASA-IMPACT/my-project.git
```

## Extend composite dispatched deployment action

1. Add a [dispatch flag in .github/workflows/dispatch.yml](https://github.com/NASA-IMPACT/veda-deploy/blob/dev/.github/workflows/dispatch.yml#L66) for the component you are adding. As in `DEPLOY_MY_COMPONENT: ${{ github.event.inputs.DEPLOY_MY_COMPONENT }}`
2. Update the [dispatch message](https://github.com/NASA-IMPACT/veda-deploy/blob/dev/.github/workflows/dispatch.yml#L46) to include your component. Eventually this will get too long and will need some thought but it is currently helpful to filter the actions and identify specific dispatches.
3. Transfer the above dispatch information to the [.github/workflows/deploy.yml workflow_call](https://github.com/NASA-IMPACT/veda-deploy/blob/dev/.github/workflows/deploy.yml#L10). The deploy action is called after the environment is set by the dispatch and for production environments is only executed after the dispatch has been approved by a maintainer.
4. Add a new [named job to deploy.yml](https://github.com/NASA-IMPACT/veda-deploy/blob/dev/.github/workflows/deploy.yml#L218) that checks the condition the deployment condition for the component and, when true, checks out the deployment action from the component's GitHub repository and passes in any relevant information like the configuration environment secret name.


## Configure domain and custom routes
VEDA platform components include options for custom subdomains and custom root paths. Coordinate how your custom resource should be configured with the team maintaining the target environment you are deploying to.