docker build --no-cache -t twkji/cpu-test .

echo "docker build -t twkji/cpu-test . done"

docker push twkji/cpu-test
echo "docker push twkji/cpu-test done"