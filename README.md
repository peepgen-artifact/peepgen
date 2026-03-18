### 1. Build up-to-date LLVM
At the project root directory:
```bash
mkdir third_party
cd scripts
./build-internal-clang.sh ../third_party/llvm <number of cpu>
```

### 2. Build Alive2
At the project root directory:
```bash
cd third_party
git clone https://github.com/AliveToolkit/alive2.git
cd alive2
mkdir build
cd build
CC="../../llvm/bin/clang" CXX="../../llvm/bin/clang++" LLVM_DIR="../../llvm/lib/cmake/llvm" cmake -GNinja -DBUILD_TV=1 -DCMAKE_BUILD_TYPE=Release ..
ninja
```
### 3. Set up gemini key token
At the project root directory:
```bash
mkdir config
```
Then create a file named
gemini_config.json and then put the apikey into it.

### 4. Run generalization
At the project root directory:
```bash
python3 generalization/peepgen_v3.py
```

