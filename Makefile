export ANDROIDSDK=$(HOME)/android/android-sdk-linux
expprt ANDROIDNDK=$(HOME)/android/android-ndk-r8c
export ANDROIDNDKVER=r8c
export ANDROIDAPI=14
DISTDIR=$(HOME)/android/python-for-android/dist/default
VERSION=0.1
KEYSTORE=$(HOME)/android/key/jnb666.keystore
ALIAS=jnb666

all: release sign

debug:
	cd $(DISTDIR); ./build.py --package org.test.kvsol --name kvsol --version $(VERSION) \
		--icon-name Solitaire --icon $(CURDIR)/images/icon.png --presplash $(CURDIR)/images/presplash.jpg \
		--ignore-path $(CURDIR)/bin/ --dir $(CURDIR) debug
	cp $(DISTDIR)/bin/kvsol-$(VERSION)-debug.apk bin/

release:
	cd $(DISTDIR); ./build.py --package org.test.kvsol --name kvsol --version $(VERSION) \
		--icon-name Solitaire --icon $(CURDIR)/images/icon.png --presplash $(CURDIR)/images/presplash.jpg \
		--ignore-path $(CURDIR)/bin/ --dir $(CURDIR) release
	cp $(DISTDIR)/bin/kvsol-$(VERSION)-release-unsigned.apk bin/

sign:
	jarsigner -verbose sigalg SHA1withRSA -digestalg SHA1 -keystore $(KEYSTORE) \
		bin/kvsol-$(VERSION)-release-unsigned.apk $(ALIAS)
	$(ANDROIDSDK)/tools/zipalign -f -v 4 bin/kvsol-$(VERSION)-release-unsigned.apk \
		bin/kvsol-$(VERSION)-release.apk
	jarsigner -verify bin/kvsol-$(VERSION)-release.apk
	rm bin/kvsol-$(VERSION)-release-unsigned.apk

install-debug:
	$(ANDROIDSDK)/platform-tools/adb install -r bin/kvsol-$(VERSION)-debug.apk

install:
	$(ANDROIDSDK)/platform-tools/adb install -r bin/kvsol-$(VERSION)-release.apk

uninstall:
	$(ANDROIDSDK)/platform-tools/adb uninstall org.test.kvsol
