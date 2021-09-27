#!/bin/bash
docker build --force-rm -t viame/detector -f Dockerfile-viame-detector .
docker build --force-rm -t viame/scorer -f Dockerfile-viame-scorer .
docker build --force-rm -t rgd/catalgo -f Dockerfile-cat-algorithm .
docker build --force-rm -t rgd/catalgobb -f Dockerfile-cat-algorithm-bb .
docker build --force-rm -t rgd/xoralgo -f Dockerfile-xor-algorithm .
docker build --force-rm -t banesullivan/kwiver:dump-klv -f Dockerfile-kwiver-dump-klv .
