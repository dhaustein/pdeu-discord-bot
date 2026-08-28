# Changelog

## [0.2.2](https://github.com/dhaustein/pdeu-discord-bot/compare/v0.2.1...v0.2.2) (2026-08-28)


### Bug Fixes

* **container:** copy lockfiles instead of bind mounting to resolve SELinux build errors ([d21b531](https://github.com/dhaustein/pdeu-discord-bot/commit/d21b5310a3b042ec23830138cf07390407a9f60c))

## [0.2.1](https://github.com/dhaustein/pdeu-discord-bot/compare/v0.2.0...v0.2.1) (2026-08-15)


### Bug Fixes

* **currency:** salvage usable rates from malformed disc cache ([c20f0e1](https://github.com/dhaustein/pdeu-discord-bot/commit/c20f0e1c16b8fd472ce0f5794d03193921c83b2c))
* **currency:** serialize refetches and serve stale cache on refresh failure ([7dc3e29](https://github.com/dhaustein/pdeu-discord-bot/commit/7dc3e295f125cdea352d8144947cdc408739d36c))
* **currency:** skip conversion when rate fetch fails with no cache ([677eb47](https://github.com/dhaustein/pdeu-discord-bot/commit/677eb47bc49d820cde8e3d9dc8dc8ddc99473a16))
* **currency:** treat malformed disc cache as cache miss ([09fe13a](https://github.com/dhaustein/pdeu-discord-bot/commit/09fe13af641026396ab1e3c6d264f56767e19fe8))

## [0.2.0](https://github.com/dhaustein/pdeu-discord-bot/compare/v0.1.0...v0.2.0) (2026-08-07)


### Features

* add basic WIP Makefile ([bfe6aa0](https://github.com/dhaustein/pdeu-discord-bot/commit/bfe6aa0504c802d165faa7f781c64bc4463c82e5))
* add Containerfile ([11b6661](https://github.com/dhaustein/pdeu-discord-bot/commit/11b6661cdfb465470c973ab34162bb57df3d9cef))
* add currency api client and model ([d96eb7b](https://github.com/dhaustein/pdeu-discord-bot/commit/d96eb7b5591313f4263b69d7b3255d9103b6b0ac))
* add currency cog ([f780617](https://github.com/dhaustein/pdeu-discord-bot/commit/f7806175b778aac81312fe33b489720124f9e4a6))
* rename module to nice ([b827723](https://github.com/dhaustein/pdeu-discord-bot/commit/b82772355484d8197829964fd5ee3a294ae09764))


### Bug Fixes

* actually atomic cache file ([40c8e3f](https://github.com/dhaustein/pdeu-discord-bot/commit/40c8e3f64f8c4609f52cd105aee538546f142375))
* ignore corrency cog completely when no currencies present ([3294a3e](https://github.com/dhaustein/pdeu-discord-bot/commit/3294a3eff7e07769afc185673f1847d248f9534c))
* indentation error in example ([980402b](https://github.com/dhaustein/pdeu-discord-bot/commit/980402beb12764422348618ffbba56f792b04827))
* pass env vars to podman run target ([ccafed8](https://github.com/dhaustein/pdeu-discord-bot/commit/ccafed86e329930c96c9526f4514b81da38872f4))
* remove not needed selinux flags ([ae16993](https://github.com/dhaustein/pdeu-discord-bot/commit/ae16993c68cf29060d0173a000dc4217f37a3887))
* selinux ([b69add9](https://github.com/dhaustein/pdeu-discord-bot/commit/b69add937e0322ba3a59852271f543f75f4cb22d))
* wrong author.id type in condition ([f5f3f0c](https://github.com/dhaustein/pdeu-discord-bot/commit/f5f3f0c931c8ded2a68b3b9d6e20ff307be0dcec))
* wrong expected rates format ([667c9ee](https://github.com/dhaustein/pdeu-discord-bot/commit/667c9ee521e1fad0f4a1f2f9ef079675789a8113))
