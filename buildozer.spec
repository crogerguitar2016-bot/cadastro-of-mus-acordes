[app]

title = Cadastro Of. Mus. Acordes

package.name = cadastroacordes
package.domain = com.croger

source.dir = .
source.include_exts = gif,py,png,jpg,jpeg,kv,atlas,ttf,otf,txt,json,pdf,htm,html,doc,docx,xls,xlsx,csv
source.exclude_dirs = .git,.buildozer,bin,__pycache__

icon.filename = %(source.dir)s/Logoapk.png

version = 1.1.0

requirements = python3,kivy,Pillow

orientation = portrait
fullscreen = 0

android.api = 36
android.minapi = 24
android.ndk = 29
android.archs = arm64-v8a

android.accept_sdk_license = True

android.permissions = READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE

p4a.branch = develop
p4a.source_dir = /home/runner/p4a


[buildozer]

log_level = 2
warn_on_root = 1
