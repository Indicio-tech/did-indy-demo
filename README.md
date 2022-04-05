# DID Indy Implementation Demo

To run the demo, first:

```sh
$ git submodule init && git submodule update
```

This will retrieve indy-vdr. Next, we must build indy-vdr:

```sh
$ cd indy-vdr
$ ./build.sh
$ mv target/release/libindy_vdr.so wrappers/python/indy_vdr/.
```

Then, from one terminal, prepare the network:

```sh
$ cd network
$ ./init-test-network.sh  # may need sudo depending on permissions
$ docker-compose up --build
```

In another terminal, run the demo script/tests:

```sh
$ poetry install
$ poetry run pytest -sv test
```
