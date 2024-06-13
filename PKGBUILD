pkgname=python-cuasm-git
_name=CuAssembler
pkgrel=1
pkgver=0.1
pkgdesc="CUDA SASS assembler/disassembler"
url="https://github.com/xuwd1/CuAssembler"
arch=(x86_64)
license=('MIT')
depends=(python-sympy  python-pyelftools)
makedepends=()
provides=()
conflicts=()
groups=()
source=()
sha256sums=()

_self_dir=$(dirname "$1")

package() {
    cd $_self_dir
    
    local site_packages=$(python -c "import site; print(site.getsitepackages()[0])")
    mkdir -p ${pkgdir}${site_packages}
    cp -r CuAsm ${pkgdir}${site_packages}/CuAsm
    
    install -Dm755 bin/cuasm.py ${pkgdir}/usr/bin/cuasm
    install -Dm755 bin/dsass.py ${pkgdir}/usr/bin/dsass
    install -Dm755 bin/hnvcc.py ${pkgdir}/usr/bin/hnvcc
    install -Dm755 bin/hcubin.py ${pkgdir}/usr/bin/hcubin
}