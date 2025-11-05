# Wan2.2 × ComfyUI で始める「本気の動画生成」入門

## 0. ゴールのイメージ

この記事のゴールはシンプルです：

> 「自分の PC で、720p / 24fps / 3〜4秒くらいの“ちゃんと観れる動画”を安定して出せるようになる」

そのためにやることは大きく 4 つ。

1. モデル構成（スタック）をちゃんと揃える
2. 解像度・フレーム設定を現実的な“最高品質ゾーン”にする
3. steps / CFG / プリセットを決めて、毎回ブレない設定を持つ
4. プロンプトを「絵コンテレベル」まで書けるようになる

これを Wan2.2 14B（テキスト→動画モデル）と ComfyUI を例にして整理します。

---

## 1. まず「スタック」を揃える

### なぜ“スタック”を意識するのか

動画生成モデルは、ざっくりいうとこういう部品の組み合わせです：

* テキストエンコーダ（プロンプト → 埋め込み）
* Diffusion 本体（ノイズから動画をつくる）
* VAE（潜在空間 ↔ 画像・動画）

別リポジトリの適当なファイルを混ぜると、

* 変な色づまり
* 破綻しやすい
* そもそも動かない

みたいな“よくわからない不具合”が出やすくなります。

なので、**公式がセットで推奨している組み合わせ（スタック）に揃える**のが鉄則です。

### Wan2.2 14B テキスト→動画の推奨スタック

Wan2.2 の ComfyUI向けリパッケージでは、だいたい次の構成が案内されています（ファイル名の一例）：

* Diffusion（高ノイズ用）

  * `wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors`
* Diffusion（低ノイズ用）

  * `wan2.2_t2v_low_noise_14B_fp8_scaled.safetensors`
* Text Encoder

  * `umt5_xxl_fp8_e4m3fn_scaled.safetensors`
* VAE

  * `wan_2.1_vae.safetensors`

そして配置先はだいたいこんな感じ：

* `ComfyUI/models/diffusion_models/`

  * `wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors`
  * `wan2.2_t2v_low_noise_14B_fp8_scaled.safetensors`
* `ComfyUI/models/text_encoders/`

  * `umt5_xxl_fp8_e4m3fn_scaled.safetensors`
* `ComfyUI/models/vae/`

  * `wan_2.1_vae.safetensors`

**ポイント**

* high / low 両方入れる（後で“デュアルパス”をやるときに必要）
* テキストエンコーダと VAE も、Wan2.2 用に用意されたものに揃える

こうしておくと、

> 「モデルのせいでおかしいのか、設定のせいでおかしいのか」

を切り分けやすくなります。

---

## 2. 解像度・フレーム・FPSの「現実的な上限」

Wan2.2 14B が狙っている“標準スペック”はだいたいこんなゾーンです：

* 解像度：**1280 × 720（いわゆる 720p）**
* フレームレート：**24fps**
* フレーム数：**81 フレーム（= 約 3.4 秒）**

理由はシンプルで：

* 32 で割り切れる解像度 → モデルの内部構造と相性がいい
* 720p → まだ現実的な VRAM で回せる上限に近い画質
* 81フレーム（8n+1） → モデルが学習時に想定している長さパターンにハマる
* 24fps → 映画っぽい自然さ ＋ 計算コストのバランスが良い

なので、入門＋本気の両方を狙うなら、`workflows.yaml` のデフォルトはこうしておくと良いです：

```yaml
defaults:
  width: 1280
  height: 720
  frames: 81
  frame_rate: 24
```

> 「まずは 720p / 3.4秒 で“ちゃんと観れる”映像を安定して出す。
> さらに綺麗にしたいなら、その後でアップスケールやフレーム補間を噛ませる」

くらいの割り切りで OK。

---

## 3. steps / CFG は“プリセット化”して迷子にならない

動画生成は、設定いじり始めた瞬間に沼にハマります。
なので、**最初からプリセットを決めておく**のが健全です。

例として、`config/workflows.yaml` にこんな風に書いておく：

```yaml
presets:
  standard:
    steps: 30
    cfg: 4.0
  high_quality:
    steps: 50
    cfg: 4.0
  maximum:
    steps: 80
    cfg: 4.0
  dual_pass:
    cfg: 3.5
    dual_stage:
      enabled: true
```

### それぞれの意味

* **standard**

  * まずはここから。
  * 720p / 81フレーム なら、30 steps で「かなり綺麗」が狙える。
* **high_quality**

  * 時間はかかるが、更に細部を詰めたいとき。
* **maximum**

  * 「時間はどうでもいいから最高を見たい」用。
  * まずは 60 steps くらいから試して、余裕があれば 80 に上げる運用でもよい。
* **dual_pass**

  * high_noise モデル → low_noise モデルの **二段階サンプリング** を使うためのモード。
  * CFG を 3.5 に落として、破綻を抑えつつディテールを詰めにいくイメージ。

CLI 側で `--preset standard|high_quality|maximum|dual_pass` みたいな引数を用意しておけば、

* 「今日は標準でざっとチェック」
* 「最終版だけ maximum で出す」

みたいな運用ができます。

---

## 4. ベースとなる `defaults` の例

ここまでをまとめた `defaults` 例はこんな感じ：

```yaml
defaults:
  negative_prompt: blurry, distorted, child, deformed, doll, multiple faces, glitch
  steps: 50          # フォールバック（preset で上書き）
  high_quality_steps: 80
  cfg: 4.0
  dual_pass_cfg: 3.5
  width: 1280
  height: 720
  frames: 81
  frame_rate: 24
  text_encoder_name: umt5_xxl_fp8_e4m3fn_scaled.safetensors
  model_name: wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors
  vae_name: wan_2.1_vae.safetensors
  filename_prefix: wan_output
  schedulers:
    stage_one: euler
    stage_two: beta
  dual_stage:
    enabled: false
    stage_one_steps: 18
    stage_two_steps: 25
    denoise: 0.45
```

* scheduler は `euler + beta` 組み合わせがよく使われるので、それを stage_one / stage_two に反映。
* dual_stage は最初は `enabled: false` にしておき、`dual_pass` プリセットでオンにする。

---

## 5. 「プロンプト＝絵コンテ」として書く

ここが一番 “動画生成らしい”部分です。

### ざっくり構造

Wan2.2 や LTX-Video が推奨しているのは、
**80〜120語くらいの「映画用ショット説明文」**です。

構造としてはこんな感じ：

1. カメラの始点と動き

   * Overhead crane shot, dolly-in, tracking, drone sweep…
2. どこで何が起きているか（シーンと被写体）

   * crosswalk in Tokyo, alpine ridge, modern lab, cultural festival…
3. ライティングと時間帯

   * golden hour, dusk, blue hour, soft diffused light, rim lighting…
4. 色とグレーディング

   * teal-and-orange grade, warm vs cool contrast, magenta-cyan palette…
5. レンズ・質感

   * anamorphic lens, shallow depth of field, 16mm film grain…
6. ムード・ジャンル

   * urban cinematic, nostalgic documentary, scientific atmosphere…

### 実例を分解してみる

#### 都市交差点の例

```yaml
wan_crowded_crosswalk:
  prompt: Overhead crane shot descending toward a bustling midday crosswalk in Tokyo Shibuya. The camera starts elevated capturing geometric pedestrian crossing lines then smoothly pans right following diverse commuters as they navigate the intersection. Glistening pavement reflects scattered puddles from light rain creating mirror surfaces. Soft diffused daylight filters through thin clouds casting even illumination with volumetric haze. Teal-and-orange color grade with shallow depth of field bokeh on background neon signs. Anamorphic lens with organic motion blur. Urban cinematic atmosphere with high contrast and crisp details capturing fabric textures and reflective surfaces.
  seed: 118
  filename_prefix: wan_crowded_crosswalk
```

ここにはすでに：

* カメラ：crane shot → pan
* 場所：Tokyo Shibuya の crosswalk
* コンディション：雨上がり
* 光：diffused daylight + volumetric haze
* 色：teal-and-orange
* レンズ：anamorphic + shallow DOF
* ムード：urban cinematic

が全部書かれていて、「何をどう撮りたいか」がほぼ完全に言語化されています。

他のテンプレ（山岳遠征・未来ラボ・文化祭・都市サイクリスト・海上研究船）も同じ構造で書いておけば、
**“動画ディレクションの型”をそのままプロンプトに転写できる**ようになります。

---

## 6. プロンプト自動拡張という考え方

毎回 100語クラスのプロンプトを手書きするのは面倒なので、
`automation/core.py` などに次のような関数を用意しておくと便利です：

```python
def _expand_prompt(base_prompt: str) -> str:
    # 1. カメラワーク候補から1〜2個
    # 2. ライティング候補から1〜2個
    # 3. 色調／グレード候補から1〜2個
    # 4. レンズ／質感候補から1〜2個
    # 5. ムード候補から1個
    # を足して、80〜120語になるまで肉付け
    ...
```

候補リストの例イメージ：

* カメラワーク
  `dolly-in, crane rising, tracking shot, drone sweep, handheld gimbal, jib shot`
* 照明
  `golden hour, blue-hour, three-point setup, rim lighting, volumetric haze`
* 色調
  `teal-and-orange grade, warm/cool contrast, bleach-bypass, neutral tones`
* レンズ
  `anamorphic lens, shallow depth of field, 16mm grain, creamy bokeh`
* ムード
  `urban cinematic, epic wilderness, futuristic clean, nostalgic warm, scientific documentary`

**ポイント**

* すでに base_prompt に近い単語が入っていたら重複追加しない
* コンフリクトしそうな組み合わせ（「neutral tones」と「彩度高め」を同時に入れるなど）は避ける
* 「1ショットでやりたいことは 1〜2 個」に抑える（詰め込みすぎない）

---

## 7. 実際の運用フロー

ここまでを「作業手順」に落とすと、だいたいこうなります。

1. **モデルダウンロードの準備**

   * `automation/main.py` に

     * high_noise
     * low_noise
     * text encoder
     * VAE
       の 4 つを download 対象として登録。
2. **ダウンロード実行**

   * `uv run python -m automation download-models`
   * だいたい 60GB 前後落ちるので、ストレージ空き要確認。
3. **`config/workflows.yaml` の defaults と presets を整える**

   * 解像度・frames・fps・モデル名・scheduler・プリセットをここで固定。
4. **`automation/core.py` に `_expand_prompt` を実装**

   * base の短いプロンプトから 80〜120語まで自動拡張できるように。
5. **テンプレプロンプトを登録**

   * `wan_crowded_crosswalk`, `wan_mountain_expedition`, … のようにシーン別テンプレを `templates:` に並べる。
6. **CLI で実行**

   * 例：
     `uv run python -m automation render --workflow wan_crowded_crosswalk --preset standard`
     `uv run python -m automation render --workflow wan_coastal_research_vessel --preset high_quality`

---

## 8. 最初の「評価軸」を決めておく

“最高品質”をちゃんと追い込みたいなら、
出てきた動画を何で評価するかも、あらかじめ決めておくと楽です。

例として、次の 5 つくらいを見ると差がわかりやすいです：

1. **解像感**

   * 被写体（人・装備・建物）の細部がどこまで潰れずに残っているか
2. **ノイズ／破綻**

   * フレーム間で手足や顔がグニャグニャしないか
3. **色とダイナミックレンジ**

   * 暗部が潰れすぎていないか、ハイライトが真っ白になりすぎていないか
4. **カメラの安定性**

   * 明らかに変な揺れやジャンプが出ていないか
5. **ムードの一貫性**

   * 最初から最後まで「同じ世界観」に見えるか

同じシーン・同じ seed で、

* `standard`
* `high_quality`
* `maximum`
* `dual_pass`

を出し比べてみると、
「自分のマシンと好みではどこが“実務的な最高”か」がだんだん見えてきます。

---

## おわりに

まとめると、この入門のキモはたった 3つです。

1. **スタックを公式推奨どおり揃える**
2. **解像度・frames・steps・CFG をプリセット化して“毎回同じ土台”から始める**
3. **プロンプトを「ショット単位の絵コンテ」として書く／自動拡張する**

ここまで整えると、

> 「とりあえず動かす」段階から
> 「自分の作品として“攻める部分”だけに集中できる」段階

に一段上がります。

あとは、あなたの世界観に合わせてテンプレを増やしていくだけです。
街、山、研究所、祭り、自転車、研究船…ここまで来たら、次は何を撮りに行きます？
