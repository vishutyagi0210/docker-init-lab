# Practice Project — tini Demo

You can tweak this practice project to demonstrate how `tini` works inside a container.

## Important Note

Before going inside the container to verify the PIDs, make sure to **remove** the following lines from your `Dockerfile`:

```dockerfile
RUN groupadd ...
RUN chown ...
USER ....
```

Once those lines are removed, you will be able to install tools inside the container (e.g., `procps` for running `ps aux`).