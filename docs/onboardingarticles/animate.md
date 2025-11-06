# Wan2.2 S2V / Animate 実装メモから読む「数式付き」入門記事

この文章は、Wan2.2 の公開コードや公式ドキュメントから**実際に読み取れる範囲**だけを使って、

* Wan-S2V（音声＋画像から動画）
* Wan-Animate（ポーズ・表情駆動のアニメーション／置換）

の中身を、数式レベルで整理した記事です。
完全な訓練コードは非公開なので、「確実な部分」と「推測を含む部分」を意識的に分けて書きます。

---

## 1. Wan2.2 の大枠：VAE ＋ Flow Matching

Wan2.2 は大雑把にいうと、

1. 動画を 3D VAE で潜在空間に圧縮して
2. その潜在空間上でフロー・マッチング（ODE 形式の生成過程）を学習する
3. Mixture-of-Experts（エキスパート混合）で巨大モデルをスケールさせる

という構造を取っています。

### 1.1 VAE による潜在表現

元の動画を表すテンソルを、ここでは次のように置きます。

$$
\boldsymbol{V}
\in \mathbb{R}^{T_{\mathrm{video}} \times H \times W \times 3}
$$

これを 3D VAE で潜在表現に圧縮します。

$$
\boldsymbol{z}_0
= \mathrm{VAE_Encode}(\boldsymbol{V}_0)
$$

生成側では、最終ステップの潜在表現から元の動画に戻します。

$$
\boldsymbol{V}
= \mathrm{VAE_Decode}(\boldsymbol{z}_T)
$$

ここで、時刻ゼロでの潜在表現を表す記号をひとまず「ゼロ番目の潜在」としておき、後段のフロー・マッチングで時間的に変形させていきます。

### 1.2 Flow Matching による生成過程

Wan2.2 は、拡散モデルのような「ノイズからの復元」ではなく、ベクトル場を直接学習するフロー・マッチングを採用しています。
潜在表現の時間発展を、連続時間の常微分方程式として書くと次のような形になります。

$$
\frac{\mathrm{d} \boldsymbol{z}*t}{\mathrm{d} t}
= \boldsymbol{v}*{\boldsymbol{\theta}}
\bigl(
\boldsymbol{z}_t,,
t,,
\boldsymbol{c}
\bigr)
$$

ここで、

* 位置ベクトルは、潜在空間上の状態を表すもの
* 時間は、生成過程の擬似時間
* 条件ベクトルは、後で出てくるテキスト・画像・音声・ポーズなどをまとめたコンディション
* ベクトル場は、ニューラルネットワーク（DiT 系）で表現されたベクトル場
* パラメータ集合は、このベクトル場を定める学習パラメータ

を表しています。

時間ゼロから時間ティーまで積分すると、次のような解の形式で書けます。

$$
\boldsymbol{z}*t
= \boldsymbol{z}*0
+ \int_0^t
\boldsymbol{v}*{\boldsymbol{\theta}}
\bigl(
\boldsymbol{z}*\tau,,
\tau,,
\boldsymbol{c}
\bigr),
\mathrm{d}\tau
$$

訓練時には、フロー・マッチング用の損失関数（ベクトル場の誤差）を最小化するようにパラメータ集合が更新されますが、損失の細かい分解（モダリティ整合、リップシンク同期など）は、公開情報だけでは特定しきれないためこの記事では深入りしません。

### 1.3 Mixture-of-Experts（概念だけ）

内部の DiT 部は、複数のエキスパートを切り替える Mixture-of-Experts になっています。
パラメータ集合は、エキスパートごとのパラメータ集合をまとめたものとして

$$
\boldsymbol{\theta}
===================

\bigl{
\boldsymbol{\theta}^{(1)},
\boldsymbol{\theta}^{(2)},
\dots,
\boldsymbol{\theta}^{(K)}
\bigr}
$$

のように分解して考えることができます。
ゲーティング関数が、時間やノイズレベルに応じて「どのエキスパートをどの程度使うか」を決めており、その結果として巨大モデルでも計算を分担しながら動かせます。

---

## 2. Wan-S2V：音声＋参照画像から動画へのマッピング

Wan-S2V は「参照画像＋音声＋テキスト」から動画を生成するモードです。
コードやドキュメントから読み取れる範囲で、入出力を数式化してみます。

### 2.1 入出力のテンソル形状

まず、入力の各モダリティをそれぞれ次のように置きます。

参照画像（たとえば顔画像）：

$$
\boldsymbol{I}
\in \mathbb{R}^{H \times W \times 3}
$$

音声波形（時間方向だけを持つ一次元信号）：

$$
\boldsymbol{A}
\in \mathbb{R}^{T_{\mathrm{audio}}}
$$

テキストプロンプト（トークン列）：

$$
\boldsymbol{P}
\in \mathbb{R}^{L_{\mathrm{prompt}}}
$$

生成される動画は、時間と空間を持つ四次元テンソルとして

$$
\boldsymbol{V}
\in \mathbb{R}^{T_{\mathrm{video}} \times H \times W \times 3}
$$

と表します。

フレーム数と音声長との関係は、おおまかに次のように考えられます。

$$
T_{\mathrm{video}}
\approx
f_{\mathrm{fps}}
\times
T_{\mathrm{sec}}
$$

ここで、フレームレートは動画の一秒あたりのフレーム数、秒数は音声の長さが秒単位で表されたものです。

### 2.2 マルチモーダルエンコード

公開コードのインターフェースから、各モダリティに専用のエンコーダが存在することが分かります。
これを抽象的に書くと、次のような三つのエンコーダがあると見なせます。

画像エンコーダ：

$$
\boldsymbol{e}_I
================

\mathrm{ImageEncoder}
\bigl(
\boldsymbol{I}
\bigr)
$$

音声エンコーダ：

$$
\boldsymbol{e}_A
================

\mathrm{AudioEncoder}
\bigl(
\boldsymbol{A}
\bigr)
$$

テキストエンコーダ：

$$
\boldsymbol{e}_P
================

\mathrm{TextEncoder}
\bigl(
\boldsymbol{P}
\bigr)
$$

それぞれの出力は「埋め込み表現」として、DiT に渡される条件ベクトルにまとめられます。

条件ベクトルをまとめて表すと、

$$
\boldsymbol{c}
==============

\mathrm{Fuse}
\bigl(
\boldsymbol{e}_I,,
\boldsymbol{e}_A,,
\boldsymbol{e}_P
\bigr)
$$

のような形になります。
実際には、クロスアテンションなどでもっと複雑に混ぜていると考えられますが、公開コードだけでは正確な式まで落とし込めないため、ここでは「融合関数」として抽象化しています。

### 2.3 潜在空間での生成

動画の潜在表現に対して、先ほどのフロー・マッチングの式を適用します。
時間ゼロでの潜在表現を

$$
\boldsymbol{z}_0
================

\mathrm{VAE_Encode}
\bigl(
\boldsymbol{V}_0
\bigr)
$$

と書き、時間に沿って変化させると次のようになります。

$$
\boldsymbol{z}_t
================

\boldsymbol{z}*0
+
\int_0^t
\boldsymbol{v}*{\boldsymbol{\theta}}
\bigl(
\boldsymbol{z}_\tau,,
\tau,,
\boldsymbol{c}
\bigr)
,\mathrm{d}\tau
$$

フローを最後まで進めた後、デコーダでもう一度ピクセル空間に戻します。

$$
\boldsymbol{V}
==============

\mathrm{VAE_Decode}
\bigl(
\boldsymbol{z}_T
\bigr)
$$

ここまでをまとめると、S2V の全体マッピングは

$$
\mathrm{S2V}
:
\bigl(
\boldsymbol{I},,
\boldsymbol{A},,
\boldsymbol{P}
\bigr)
;\longmapsto;
\boldsymbol{V}
$$

という関数として見なすことができます。

### 2.4 推論時のパラメータとモデル規模

S2V のタスクとして「十四ビリオンパラメータ級」のモデルが提供されています。
パラメータ数を表す記号で書くと、

$$
\lvert
\boldsymbol{\theta}_{\mathrm{S2V}}
\rvert
\approx
1.4 \times 10^{10}
$$

というオーダーになります。

単一の八十ギガバイト GPU を想定した構成が標準ですが、ＦＳＤＰや Ulysses などを用いると、エイト枚の GPU で分散しながら推論する構成も公式に案内されています。
分散した場合、一枚あたりのおおまかな要求ＶＲＡＭは

$$
\mathrm{VRAM}_{\mathrm{per\text{-}GPU}}
\approx
\frac{
80
}{
8
}
;\mathrm{GB}
$$

のように書けます。
オフロードや量子化を駆使すれば十六ギガバイト級のカードで動かしたという報告もありますが、これは公式の保証ではなく、実験的な目安です。

---

## 3. Wan-Animate：ポーズ・表情・フロー駆動の動画変換

Wan-Animate は、入力動画から

* 骨格ポーズ
* 顔の特徴
* オプティカルフロー

などを抽出し、それを条件として動画を生成・置換するモードです。

### 3.1 前処理フェーズの形式化

前処理スクリプトは、入力動画と参照画像を読み込み、時刻ごとのポーズや顔、フローをファイル群として保存します。
動画を表すテンソルを次のようにします。

$$
\boldsymbol{V}^{\mathrm{src}}
\in \mathbb{R}^{T \times H \times W \times 3}
$$

参照画像を次のように置きます。

$$
\boldsymbol{I}^{\mathrm{ref}}
\in \mathbb{R}^{H \times W \times 3}
$$

前処理の出力は、少なくとも次の三種類の系列を含んでいると考えられます。

骨格シーケンス：

$$
\bigl{
\boldsymbol{s}*t
\bigr}*{t=1}^{T}
================

\mathrm{SkeletonExtract}
\bigl(
\boldsymbol{V}^{\mathrm{src}}
\bigr)
$$

顔特徴シーケンス：

$$
\bigl{
\boldsymbol{f}*t
\bigr}*{t=1}^{T}
================

\mathrm{FaceFeatureExtract}
\bigl(
\boldsymbol{V}^{\mathrm{src}}
\bigr)
$$

オプティカルフロー：

$$
\bigl{
\boldsymbol{o}*t
\bigr}*{t=1}^{T}
================

\mathrm{OpticalFlow}
\bigl(
\boldsymbol{V}^{\mathrm{src}}
\bigr)
$$

これらをまとめて、「前処理済みデータ集合」としておきます。

$$
\mathcal{D}
===========

\bigl{
\bigl(
\boldsymbol{s}_t,,
\boldsymbol{f}_t,,
\boldsymbol{o}*t
\bigr)
\bigr}*{t=1}^{T}
$$

生成フェーズでは、この集合と参照画像を入力として、最終的な動画を生成します。

$$
\boldsymbol{V}^{\mathrm{out}}
=============================

\mathrm{Animate}
\bigl(
\mathcal{D},,
\boldsymbol{I}^{\mathrm{ref}};,
\mathrm{mode}
\bigr)
$$

ここで、モードはアニメーションモード、置換モードなどのスイッチを表します。

### 3.2 モードの違い：アニメーションと置換

アニメーションモードでは、参照画像のキャラクターを用いて、入力動画のポーズや表情、動きに沿った新しい動画を生成します。
このとき、条件ベクトルはおおまかに次のようになります。

$$
\boldsymbol{c}_{\mathrm{anim}}
==============================

\mathrm{Fuse}
\Bigl(
\bigl{
\boldsymbol{s}*t
\bigr}*{t=1}^{T},,
\bigl{
\boldsymbol{f}*t
\bigr}*{t=1}^{T},,
\boldsymbol{I}^{\mathrm{ref}}
\Bigr)
$$

置換モードでは、元の動画の背景を保ちつつ、人物やキャラクターだけを参照画像で置き換えるような動作になります。
このとき、潜在表現を

* 背景成分
* キャラクター成分
* 時間的一貫性の補助成分

のように分ける実装が示唆されています。
潜在表現を三つのチャネルに分けるイメージで書くと、

背景側：

$$
\boldsymbol{z}_t^{\mathrm{bg}}
$$

参照キャラ側：

$$
\boldsymbol{z}_t^{\mathrm{ref}}
$$

時間補助側：

$$
\boldsymbol{z}_t^{\mathrm{temp}}
$$

これらを結合した全体の潜在表現は、

$$
\boldsymbol{z}_t
================

\bigl[
\boldsymbol{z}_t^{\mathrm{bg}},,
\boldsymbol{z}_t^{\mathrm{ref}},,
\boldsymbol{z}_t^{\mathrm{temp}}
\bigr]
$$

と表せます。
置換モードでは、とくに背景側の潜在を元動画から強く引き継ぐことで、「背景は維持しつつ人物だけ差し替える」という挙動を実現していると考えられます。

### 3.3 Relighting LoRA の効果

置換モードには「照明を合わせるための LoRA」を使うオプションもあります。
これは、基礎モデルのパラメータに小さな補正を加える形で表現できます。

基礎モデルのパラメータ集合を

$$
\boldsymbol{\theta}_{\mathrm{base}}
$$

照明調整用の LoRA による変化量を

$$
\Delta \boldsymbol{\theta}_{\mathrm{relight}}
$$

とすると、推論時に実際に使われる有効なパラメータ集合は

$$
\boldsymbol{\theta}_{\mathrm{eff}}
==================================

\boldsymbol{\theta}*{\mathrm{base}}
+
\Delta \boldsymbol{\theta}*{\mathrm{relight}}
$$

と書けます。
この補正により、元動画の光源方向・明るさと、合成されるキャラクターの見た目とのギャップを減らすことができます。

---

## 4. 解像度・フレーム数・メモリと複雑度

### 4.1 解像度と標準設定

Wan2.2 のビデオモデルは、十六対九のアスペクト比で四百八十ピーや七百二十ピーをサポートしています。
代表的な解像度は次のような組み合わせです。

四百八十ピー相当：

$$
\bigl(
H,,
W
\bigr)
======

\bigl(
480,,
848
\bigr)
$$

七百二十ピー相当：

$$
\bigl(
H,,
W
\bigr)
======

\bigl(
720,,
1280
\bigr)
$$

ワークフローやツールによっては、一〇二四×七〇四のような解像度も用いられますが、これはモデルの標準解像度というより、周辺ツール側の便宜上の設定である場合が多いです。

### 4.2 フレーム数と音声長

フレーム数と音声長の関係は、S2V でも Animate でも基本的には同じです。

フレームレート：

$$
f_{\mathrm{fps}}
$$

動画長（秒）：

$$
T_{\mathrm{sec}}
$$

とすると、おおまかなフレーム数は

$$
T_{\mathrm{video}}
\approx
f_{\mathrm{fps}}
\times
T_{\mathrm{sec}}
$$

となります。
たとえば、二十四フレーム毎秒の動画で五秒間の音声を使うと、だいたい百二十フレーム前後の動画になります。

### 4.3 注意計算の計算量と分散

DiT のようなトランスフォーマーベースのモデルでは、自己注意の計算量はシーケンス長の二乗に比例します。
潜在空間内のトークン数を

$$
L
$$

自己注意の計算量を

$$
\mathcal{O}\bigl(L^2\bigr)
$$

と表すと、Ulysses のような手法でシーケンスをエヌ分割して計算する場合、各分割あたりの計算量は

$$
\mathcal{O}
\Bigl(
\bigl(L / n\bigr)^2
\Bigr)
======

\mathcal{O}
\Bigl(
L^2 / n^2
\Bigr)
$$

となります。
さらに、複数の GPU に分散することで、実際に一枚あたりが処理するトークン数を減らし、メモリ要求を抑えています。

---

## 5. 「確実な部分」と「推測を含む部分」の整理

最後に、この記事で触れた内容を、公開情報との対応という観点でざっくり整理しておきます。

### 5.1 確実に言える部分

次のような要素は、公式のドキュメント・コード・ブログなどから直接支持されている範囲です。

* 動画を三次元ＶＡＥで潜在空間に圧縮し、フロー・マッチングで生成過程を学習していること
* フロー・マッチングの基本式（ベクトル場による常微分方程式）の形
* 画像・音声・テキストの三モダリティを埋め込みとして扱う構造
* Animate で、ポーズ・顔特徴・オプティカルフローを前処理で抽出していること
* モデル規模がおおむね十四ビリオンパラメータ級であること
* 十六対九の四百八十ピー・七百二十ピーを標準としていること
* 単一八十ギガバイト GPU またはエイト枚分散での推論が想定されていること

これらは、数式として書き直してもほぼ矛盾しないと考えてよい部分です。

### 5.2 推測を含む部分

一方で、次のような部分は「公開情報から自然に想像できるが、厳密なソースはまだ出ていない」領域です。

* 条件ベクトルの具体的な融合方法（どの層でどのようにクロスアテンションしているか）
* MoE のエキスパート分割ルール（空間方向、時間方向、ノイズレベルなど）
* Wan-S2V 特有の追加損失（モダリティ整合やリップシンク同期）の具体的な式
* Animate 置換モード内部で、背景・キャラクター・時間的補助をどう分解・統合しているかの詳細
