制作了PKGBUILD以便在arch下安装到系统：

```
cd /path/that/contains/PKGBUILD  #确定你的cwd在PKGBUILD所在目录，也就是这个repo的根目录
makepkg -si

```

或者

```
cd /path/that/contains/PKGBUILD  #确定你的cwd在PKGBUILD所在目录，也就是这个repo的根目录
makepkg -s
sudo pacman -U python-cuasm-git-0.1-1-x86_64.pkg.tar.zst

```

效果：安装`cuasm`,`dsass`,`hnvcc`和`hcubin`到`/usr/bin`