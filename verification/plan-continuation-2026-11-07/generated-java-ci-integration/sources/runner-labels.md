
This repository contains the source code used to create the VM images for [GitHub-hosted runners](https://docs.github.com/en/actions/using-github-hosted-runners/about-github-hosted-runners) used for Actions, as well as for [Microsoft-hosted agents](https://docs.microsoft.com/en-us/azure/devops/pipelines/agents/hosted?view=azure-devops#use-a-microsoft-hosted-agent) used for Azure Pipelines.
To build a VM machine from this repo's source, see the [instructions](docs/create-image-and-azure-resources.md).

## Available Images

| Image | Architecture | YAML Label | Included Software |
| --------------------|--------------|---------------------|------------------|
| Ubuntu 26.04<br>![Endpoint Badge](https://img.shields.io/endpoint?url=https%3A%2F%2Fgist.githubusercontent.com%2Fhosted-runners-images-bot%2F79267492faab096d04cdd25ce7014cec%2Fraw%2Fubuntu26.json) | x64 | `ubuntu-26.04` | [ubuntu-26.04] |
| Ubuntu 26.04 Arm64<br>![Endpoint Badge](https://img.shields.io/endpoint?url=https%3A%2F%2Fgist.githubusercontent.com%2Fhosted-runners-images-bot%2F79267492faab096d04cdd25ce7014cec%2Fraw%2Fubuntu26-arm64.json) | arm64 | `ubuntu-26.04-arm` | [ubuntu-26.04-arm64] |
| Ubuntu 24.04<br>![Endpoint Badge](https://img.shields.io/endpoint?url=https%3A%2F%2Fgist.githubusercontent.com%2Fhosted-runners-images-bot%2F79267492faab096d04cdd25ce7014cec%2Fraw%2Fubuntu24.json) | x64 | `ubuntu-latest` or `ubuntu-24.04` | [ubuntu-24.04] |
| Ubuntu 24.04 Arm64<br>![Endpoint Badge](https://img.shields.io/endpoint?url=https%3A%2F%2Fgist.githubusercontent.com%2Fhosted-runners-images-bot%2F79267492faab096d04cdd25ce7014cec%2Fraw%2Fubuntu24-arm64.json) | arm64 | `ubuntu-24.04-arm` | [ubuntu-24.04-arm64] |
| Ubuntu 22.04<br>![Endpoint Badge](https://img.shields.io/endpoint?url=https%3A%2F%2Fgist.githubusercontent.com%2Fhosted-runners-images-bot%2F79267492faab096d04cdd25ce7014cec%2Fraw%2Fubuntu22.json) | x64 | `ubuntu-22.04` | [ubuntu-22.04] |
| Ubuntu 22.04 Arm64<br>![Endpoint Badge](https://img.shields.io/endpoint?url=https%3A%2F%2Fgist.githubusercontent.com%2Fhosted-runners-images-bot%2F79267492faab096d04cdd25ce7014cec%2Fraw%2Fubuntu22-arm64.json) | arm64 | `ubuntu-22.04-arm` | [ubuntu-22.04-arm64] |
| Ubuntu Slim<br>![Endpoint Badge](https://img.shields.io/endpoint?url=https%3A%2F%2Fgist.githubusercontent.com%2Fhosted-runners-images-bot%2F79267492faab096d04cdd25ce7014cec%2Fraw%2Fubuntu-slim.json) | x64 | `ubuntu-slim` | [ubuntu-slim] |
| Xcode 27 [![preview](https://img.shields.io/badge/preview-0969DA?style=flat&logoColor=white)](https://github.com/actions/runner-images/issues/14404)<br>![Endpoint Badge](https://img.shields.io/endpoint?url=https%3A%2F%2Fgist.githubusercontent.com%2Fhosted-runners-images-bot%2F79267492faab096d04cdd25ce7014cec%2Fraw%2Fxcode-27-arm64.json) | arm64 | `xcode-27` or `xcode-27-xlarge` | [xcode-27] |
| macOS 26<br>![Endpoint Badge](https://img.shields.io/endpoint?url=https%3A%2F%2Fgist.githubusercontent.com%2Fhosted-runners-images-bot%2F79267492faab096d04cdd25ce7014cec%2Fraw%2Fmacos-26.json) | x64 | `macos-latest-large`, `macos-26-intel`, `macos-26-large` | [macOS-26] |
| macOS 26 Arm64<br>![Endpoint Badge](https://img.shields.io/endpoint?url=https%3A%2F%2Fgist.githubusercontent.com%2Fhosted-runners-images-bot%2F79267492faab096d04cdd25ce7014cec%2Fraw%2Fmacos-26-arm64.json) | arm64 | `macos-latest`, `macos-26` or `macos-26-xlarge` | [macOS-26-arm64] |
| macOS 15<br>![Endpoint Badge](https://img.shields.io/endpoint?url=https%3A%2F%2Fgist.githubusercontent.com%2Fhosted-runners-images-bot%2F79267492faab096d04cdd25ce7014cec%2Fraw%2Fmacos-15.json) | x64 | `macos-15-large`, or `macos-15-intel` | [macOS-15] |
| macOS 15 Arm64<br>![Endpoint Badge](https://img.shields.io/endpoint?url=https%3A%2F%2Fgist.githubusercontent.com%2Fhosted-runners-images-bot%2F79267492faab096d04cdd25ce7014cec%2Fraw%2Fmacos-15-arm64.json) | arm64 | `macos-15`, or `macos-15-xlarge` | [macOS-15-arm64] |
| macOS 14 [![deprecated](https://img.shields.io/badge/deprecated-E5534B?style=flat&logoColor=white)](https://github.com/actions/runner-images/issues/15226)<br>![Endpoint Badge](https://img.shields.io/endpoint?url=https%3A%2F%2Fgist.githubusercontent.com%2Fhosted-runners-images-bot%2F79267492faab096d04cdd25ce7014cec%2Fraw%2Fmacos-14.json) | x64 | `macos-14` | [macOS-14] |
| Windows Server 2025<br>![Endpoint Badge](https://img.shields.io/endpoint?url=https%3A%2F%2Fgist.githubusercontent.com%2Fhosted-runners-images-bot%2F79267492faab096d04cdd25ce7014cec%2Fraw%2Fwin25-vs2026.json) | x64 | `windows-latest`, `windows-2025`, or `windows-2025-vs2026` | [windows-2025-vs2026] |
| Windows Server 2022<br>![Endpoint Badge](https://img.shields.io/endpoint?url=https%3A%2F%2Fgist.githubusercontent.com%2Fhosted-runners-images-bot%2F79267492faab096d04cdd25ce7014cec%2Fraw%2Fwin22.json) | x64 | `windows-2022` | [windows-2022] |
| Windows 11 Arm64 with Visual Studio 2026<br>![Endpoint Badge](https://img.shields.io/endpoint?url=https%3A%2F%2Fgist.githubusercontent.com%2Fhosted-runners-images-bot%2F79267492faab096d04cdd25ce7014cec%2Fraw%2Fwin11-vs2026-arm64.json) | arm64 | `windows-11-arm` or `windows-11-vs2026-arm` | [windows-11-vs2026-arm64] |

> [!IMPORTANT]
> All macOS 14 images retired from GitHub Actions on November 2, 2026. macOS 14 Intel images remain available only in Azure DevOps until November 23, 2026. This extension does not apply to Arm64 images. See the [retirement announcement](https://github.com/actions/runner-images/issues/15226) for brownout dates and migration details.

### Label scheme

- In general the `-latest` label is used for the latest OS image version that is GA.
- Before moving the `-latest` label to a new OS version we will announce the change and give sufficient lead time for users to update their workflows.
- The `-xlarge` and `-large` suffixes are unique to macOS images and are only available for GitHub Actions. Learn more about [GitHub Actions larger runners](https://docs.github.com/en/actions/reference/runners/larger-runners#available-macos-larger-runners-and-labels).

[ubuntu-26.04]: https://github.com/actions/runner-images/blob/main/images/ubuntu/Ubuntu2604-Readme.md
[ubuntu-26.04-arm64]: https://github.com/actions/runner-images/blob/main/images/ubuntu/Ubuntu2604-Arm64-Readme.md
[ubuntu-24.04]: https://github.com/actions/runner-images/blob/main/images/ubuntu/Ubuntu2404-Readme.md
[ubuntu-24.04-arm64]: https://github.com/actions/runner-images/blob/main/images/ubuntu/Ubuntu2404-Arm64-Readme.md
[ubuntu-22.04]: https://github.com/actions/runner-images/blob/main/images/ubuntu/Ubuntu2204-Readme.md
[ubuntu-22.04-arm64]: https://github.com/actions/runner-images/blob/main/images/ubuntu/Ubuntu2204-Arm64-Readme.md
[ubuntu-slim]: https://github.com/actions/runner-images/blob/main/images/ubuntu-slim/ubuntu-slim-Readme.md
[windows-2025-vs2026]: https://github.com/actions/runner-images/blob/main/images/windows/Windows2025-VS2026-Readme.md
[windows-2022]: https://github.com/actions/runner-images/blob/main/images/windows/Windows2022-Readme.md
[windows-11-vs2026-arm64]: https://github.com/actions/runner-images/blob/main/images/windows/Windows11-VS2026-Arm64-Readme.md
[macOS-14]: https://github.com/actions/runner-images/blob/main/images/macos/macos-14-Readme.md
[macOS-15]: https://github.com/actions/runner-images/blob/main/images/macos/macos-15-Readme.md
