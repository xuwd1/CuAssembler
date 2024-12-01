# CuAsm SM90测试

## 导出命令

1. 通过`find`定位到CUBLAS库的位置：

```bash
find /opt -iname '*libcublas*' 2>/dev/null
```

2. 分别对`libcublas.so`和`libcublasLt.so`进行导出：

```bash

# libcublas.so
cuobjdump -sass -arch sm_90 /opt/cuda/targets/x86_64-linux/lib/libcublas.so > libcublas.sm_90.sass  

# libcublasLt.so
cuobjdump -sass -arch sm_90 /opt/cuda/targets/x86_64-linux/lib/libcublasLt.so > libcublasLt.sm_90.sass
```

### Caveats

1. 现在注意到`libcublasLt.so`的体积明显大于`libcublas.so`. 也就是说现在CUBLASLT的功能很可能远多于CUBLAS.

2. 注意到只有`libcublasLt.so`中包含使用了GMMA的代码 (HGMMA, IGMMA等)，而`libcublas.so`中无论是使用`-arch sm_90`还是`-arch sm_90a`都完全没有发现任何使用了GMMA的代码。

3. 此外，发现使用`-arch sm_90`和`-arch sm_90a`导出的`libcublas.so`的结果是完全一样的，这说明`libcublas.so`中并没有使用`sm_90a`的特性。



## CuInsFeeder类的适配




## Interesting finding

#### 1. SM90的Control Code编码

SM90的Control Code编码似乎和SM80完全相同. 目前我们简单将CuInsFeeder中SM90相关的功能映射到SM80,由其进行`trans`（产生一份带有Control Code的SASS代码），得到的结果看起来非常合理.

- 这里的合理包括stall cycle的设置，也包括barrier的设置

#### 2. SM90的FP16 HMMA 16818指令的倒数吞吐率

由改造后的CuInsFeeder生成的`trans`代码中，我们能看到如下的内容：

```
[B------:R-:W-:-:S06]    HMMA.16816.F32.BF16 R32, R68, R86, R32 ; 
[B-1----:R-:W-:-:S06]    HMMA.16816.F32.BF16 R36, R88, R86, R36 ; 
[B------:R-:W-:-:S06]    HMMA.16816.F32.BF16 R40, R88, R84, R40 ; 
[B------:R-:W-:-:S06]    HMMA.16816.F32.BF16 R44, R88, R82, R44 ; 
```

可以注意到，SM90的HMMA.16816.F32.BF16的倒数吞吐率竟然是**6**！
- 相较于A100的两组无限型，A100的该指令倒数吞吐率是**8**
- 也就是说H100的tensor速度实际上相较于A100有进一步的提升，这对于我们来说是一个非常好的消息

#### 3. 新指令：`VIADD`

目前注意到几种形式：

1. `VIADD R170, R170, 0xffffffff ;`
2. `VIADD R5, R4, UR5 ; `
3.
   ```
   [B------:R-:W-:-:S02]  VIADD R163, R6.reuse, 0x400 ;  
   [B------:R-:W-:-:S02]  VIADD R7, R6.reuse, 0x800 ;    
   [B------:R-:W-:-:S01]  VIADD R6, R6, 0xc00 ;   
   ```

总的来说：

- dst和src1都是`R`寄存器
- src2可以是立即数，也可以是`UR`寄存器
- src1可以复用
- 注意到倒数吞吐率是2

看来似乎是一种地位类似于`UIMAD`的新型指令，目前不清楚这个`V`代表的是什么. 感觉似乎是一种减小了读数开销和运算开销的快速整数加法指令. 


#### 4. 新指令：`R2UR`

只有一种形式：


```
[B------:R-:W-:-:S02] @!P1 R2UR UR4, R160 ; 
[B------:R-:W-:-:S02] @!P0 R2UR UR4, R5 ;   
```


- 明显是AMDGPU中的`readfirstlane`的类似物. 功能应当是把向量寄存器的第一个Lane转移到一个UR寄存器中. 
- 注意到倒数吞吐率是2


#### 5. TMA指令：`UTMALDG`, `UTMASTG`, `UTMACMDFLUSH`


TODO


#### 6. WARPGROUP指令：`WARPGROUP.ARRIVE`, `WARPGROUP.DEPBAR.LE`


TODO