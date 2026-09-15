# openEuler riscv64 support

The **external artifact provider** is the registry and download service chosen
by the operator for RISC-V binaries, images, and RPMs. It is not an ocboot
default and it is not an upstream endorsement. This distinction matters
because K3s and Cloudpods do not currently publish every riscv64 artifact that
this deployment path needs.

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
- The external provider supplies checksum-pinned K3s binary and air-gap image
  assets, a Cloudpods RPM repository, and all images listed in the example.
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
already-running Cloudpods cluster does not retain the external RPM and K3s
download configuration. Put that mapping in a separate YAML file (either as
the root mapping or under a `riscv64` key) and run:

```bash
./ocboot.sh add-node \
  --riscv64-config riscv64-artifacts.yml \
  --runtime qemu \
  PRIMARY_MASTER_IP NEW_NODE_IP
```

ocboot validates SHA-256 values before using downloaded K3s assets. It uses a
temporary `.part` file, deletes failed or mismatched downloads, and caches the
validated provider metadata beside the air-gap assets for reproducible
retries. The cache does not make the provider an ocboot default.

Set `riscv64.cloudpods.monitor_disable: true` only when the provider does not
publish the monitoring images required by the selected Cloudpods version.
That setting leaves core compute and control-plane deployment available but
does not constitute monitoring validation.
