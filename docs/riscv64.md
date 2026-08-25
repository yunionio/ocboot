# openEuler riscv64 support

The **external artifact provider** is the registry and download service chosen
by the operator for Cloudpods images and RPMs. It is not an ocboot default or
an upstream endorsement. K3s RISC-V assets instead come from the official
[`yunionio/k3s` v1.28.5+k3s2 release](https://github.com/yunionio/k3s/releases/tag/v1.28.5%2Bk3s2)
and are bundled by the ocboot Dockerfile with SHA-256 verification. Use an
ocboot image rebuilt from this Dockerfile; older images may contain K3s
`v1.28.5+k3s1` RISC-V assets and fail the checksum check.

This path targets openEuler 24.03 LTS SP3 and K3s. Native Kubernetes mode is
rejected for riscv64. Existing amd64 and arm64 behavior is unchanged unless a
configuration explicitly declares a riscv64 target.

## Requirements

- Each RISC-V host declares `target_architecture: riscv64`. ocboot compares
  that declaration with `uname -m` before changing the host.
- KVM and TUN devices are required when the node is a Cloudpods compute host.
- The memory and cpuset cgroup v2 controllers must be available. On the
  supported openEuler U-Boot layout, ocboot can add the cgroup v2 kernel
  parameter and reboot once.
- The ocboot image bundles the K3s RISC-V binary and air-gap images. ocboot
  checks their SHA-256 before use and does not download RISC-V K3s at runtime.
- The external provider supplies a Cloudpods RPM repository and the images
  listed in the example.
- Signed RPM metadata and packages are recommended. Unsigned repositories
  require both checks to be disabled explicitly and emit a warning.
- `flannel` and `calico` are the supported cluster CNI values. CNI means the
  pod-network implementation shared by the whole cluster; it cannot differ
  by node architecture.

Copy `config-example-openeuler-riscv64.yml`, replace every example artifact,
checksum, tag, address, and password, then run:

```bash
./ocboot.sh install config-openeuler-riscv64.yml
```

The `riscv64` mapping is also required when adding a RISC-V node because an
already-running Cloudpods cluster does not retain the external Cloudpods RPM
and image configuration. Put that mapping in a separate YAML file (either as
the root mapping or under a `riscv64` key) and run:

```bash
./ocboot.sh add-node \
  --riscv64-config riscv64-artifacts.yml \
  --runtime qemu \
  PRIMARY_MASTER_IP NEW_NODE_IP
```

ocboot validates bundled RISC-V K3s asset SHA-256 values before use. The
upstream amd64/arm64 assets stay at `v1.28.5+k3s1`; RISC-V uses the yunionio
`v1.28.5+k3s2` build of the same Kubernetes patch version. Mixed-architecture
operation still requires testing with the selected Cloudpods images.

Set `riscv64.cloudpods.monitor_disable: true` only when the provider does not
publish the monitoring images required by the selected Cloudpods version.
That setting leaves core compute and control-plane deployment available but
does not constitute monitoring validation.
