# Flow Matching と DDPM の比較（厳密めインストール用メモ）

このドキュメントでは、DDPM（拡散モデル）と Flow Matching（特に Rectified Flow 型）の関係を、  
数式を使ってできるだけ厳密に整理します。

記号はすべて数式ブロック内で定義し、本文中では「上の式の記号」という形で参照します。  
インライン数式は使いません。

---

## 1. 生成モデリングの共通設定

まず、共通の前提をそろえます。

状態空間を実ベクトル空間とします。

$$
\mathbb{R}^d
$$

ここで

- データ分布を次のように表します。

$$
\pi_1 \ \text{on}\ \mathbb{R}^d
$$

- ベース分布（ノイズ分布）を標準正規分布とします。

$$
\pi_0 = \mathcal{N}(0, I_d)
$$

目標は、ベース分布からデータ分布へ写す確率写像（あるいはその連続時間版）を学習することです。

$$
x_0 \sim \pi_0
\quad\Longrightarrow\quad
x_1 \sim \pi_1
$$

---

## 2. DDPM（離散時間拡散モデル）

### 2.1 前向き拡散過程

DDPM では、元データのサンプルを次のように書きます。

$$
x_0 \sim \pi_1
$$

この上に、時間ステップ

$$
t = 1,2,\dots,T
$$

のマルコフ連鎖を定義します。前向き過程は

$$
q(x_{1:T} \mid x_0)=
\prod_{t=1}^T q(x_t \mid x_{t-1})
$$

と書きます。各ステップはガウス分布です。

$$
q(x_t \mid x_{t-1})=
\mathcal{N}
\bigl(
  x_t;\,
  \sqrt{1 - \beta_t}\, x_{t-1},\,
  \beta_t I
\bigr),
\qquad
\beta_t \in (0,1)
$$

ここで \(\beta_t\) は「ノイズスケジュール」です。

このマルコフ連鎖を繰り返すと、十分大きな \(t\) で \(x_t\) はほぼ標準正規分布に近づきます。

この連鎖は閉じた形で

$$
q(x_t \mid x_0)=
\mathcal{N}
\bigl(
  x_t;\,
  \sqrt{\bar{\alpha}_t}\, x_0,\,
  (1 - \bar{\alpha}_t) I
\bigr)
$$

と書けます。ここで

$$
\alpha_t = 1 - \beta_t,
\qquad
\bar{\alpha}_t = \prod_{s=1}^t \alpha_s
$$

です。

### 2.2 逆向き生成過程

生成時には、終端分布を

$$
p(x_T) = \mathcal{N}(0, I)
$$

とし、逆向きマルコフ連鎖

$$
p_\theta(x_{0:T})=
p(x_T)
\prod_{t=1}^T p_\theta(x_{t-1} \mid x_t)
$$

を用います。

各逆遷移は

$$
p_\theta(x_{t-1} \mid x_t)=
\mathcal{N}
\bigl(
  x_{t-1};\,
  \mu_\theta(x_t, t),\,
  \sigma_t^2 I
\bigr)
$$

というガウス分布でパラメタライズします。  
分散 \(\sigma_t^2\) は前向き過程から解析的に求めた値を使う設計が一般的です。

### 2.3 DDPM の簡略損失

前向き過程の閉形式を用いると、任意のステップ \(t\) について

$$
x_t=
\sqrt{\bar{\alpha}_t}\, x_0
+
\sqrt{1 - \bar{\alpha}_t}\, \varepsilon,
\qquad
\varepsilon \sim \mathcal{N}(0, I)
$$

と書けます。

ニューラルネットワーク \(\varepsilon_\theta\) を、  
ノイズ \(\varepsilon\) を予測する関数として訓練する簡略損失は次の形です。

$$
L_{\mathrm{DDPM}}(\theta)=
\mathbb{E}_{x_0 \sim \pi_1,\;
           \varepsilon \sim \mathcal{N}(0,I),\;
           t \sim \mathrm{Unif}\{1,\dots,T\}}
\bigl[
  \|
    \varepsilon
    -
    \varepsilon_\theta(x_t, t)
  \|^2
\bigr]
$$

ここで \(\varepsilon_\theta\) は「ノイズ予測ネット」です。

---

## 3. 連続時間拡散モデルと確率フロー ODE

DDPM を時間ステップ幅を 0 に近づける極限で見ると、  
スコアベース拡散モデルと同様に「確率微分方程式（SDE）」として書くことができます。

### 3.1 前向き SDE

連続時間を

$$
t \in [0,1]
$$

とし、前向き SDE を

$$
\mathrm{d}x_t=
f(x_t, t)\,\mathrm{d}t
+
g(t)\,\mathrm{d}w_t
$$

と書きます。

ここで

- \(f(x_t, t)\) はドリフト（決定論的な変化）
- \(g(t)\) は拡散係数（ノイズの強さ）
- \(w_t\) は標準ブラウン運動

です。

### 3.2 確率フロー ODE

Song らは、この SDE に対応する「確率フロー ODE」を次のように定義します。

$$
\mathrm{d}x_t=
\Bigl(
  f(x_t, t)
  -
  \tfrac{1}{2}
  g(t)^2
  \nabla_x \log p_t(x_t)
\Bigr)\,
\mathrm{d}t
$$

ここで \(p_t(x)\) は時刻 \(t\) における \(x_t\) の密度です。

この ODE の解の分布列 \(\{p_t\}_{t \in [0,1]}\) が、  
対応する SDE の分布列と一致することが知られています。  
したがって、確率フロー ODE を積分することでも、  
ベース分布からデータ分布への生成が可能です。

---

## 4. Flow Matching の一般的定式化

Flow Matching は、Continuous Normalizing Flows（CNF）を**シミュレーションなしで**学習する枠組みです。

### 4.1 CNF（連続正規化フロー）

CNF では、連続時間 ODE

$$
\frac{\mathrm{d}x_t}{\mathrm{d}t}=
v_\theta(x_t, t),
\qquad
t \in [0,1]
$$

を用います。初期状態は

$$
x_0 \sim \pi_0
$$

です。

ベクトル場 \(v_\theta\) はニューラルネットワークでパラメタライズされます。

### 4.2 確率パスの定義

Flow Matching のポイントは、「中間時刻の分布」を**任意の確率パス**として指定できることです。

ベース分布とデータ分布の間を結ぶパスとして、  
条件付き分布

$$
p_t(x \mid x_0, x_1),
\qquad
t \in [0,1]
$$

を定義します。ここで \(x_0\) はベース側サンプル、\(x_1\) はデータ側サンプルです。

このとき周辺分布は

$$
p_t(x)=
\iint
  p_t(x \mid x_0, x_1)\,
  \pi_0(x_0)\,
  \pi_1(x_1)\,
\mathrm{d}x_0\,\mathrm{d}x_1
$$

となります。

### 4.3 目標ベクトル場

条件付きパスの平均軌道を

$$
\tilde{x}_t(x_0, x_1)=
\mathbb{E}
\bigl[
  x_t \mid x_0, x_1
\bigr]
$$

その時間微分を「条件付き速度」

$$
v_t(x_0, x_1, t)=
\frac{\mathrm{d}}{\mathrm{d}t}
\tilde{x}_t(x_0, x_1)
$$

とします（解析的に計算できるようなパスを設計します）。

このとき、目標ベクトル場 \(u_t(x)\) を

$$
u_t(x)=
\mathbb{E}
\bigl[
  v_t(x_0, x_1, t)
  \mid
  x_t = x
\bigr]
$$

と定義すると、\(u_t\) は連続の方程式

$$
\frac{\partial}{\partial t}
p_t(x)
+
\nabla_x \cdot
\bigl(
  p_t(x)\,u_t(x)
\bigr)= 0
$$

を満たし、ODE

$$
\frac{\mathrm{d}x_t}{\mathrm{d}t}=
u_t(x_t)
$$

の解の分布列 \(\{p_t\}\) を再現することが示されます。

### 4.4 Flow Matching 損失

Flow Matching の学習は、この \(u_t\) をニューラルネット \(v_\theta\) で近似する問題として定式化されます。

サンプリング手順（1 ステップ分）は

1. \(x_0 \sim \pi_0\) をサンプル
2. \(x_1 \sim \pi_1\) をサンプル
3. \(t \sim \mathrm{Unif}(0,1)\) をサンプル
4. パスから \(x_t\) と \(v_t(x_0, x_1, t)\) を計算

とし、損失を

$$
L_{\mathrm{FM}}(\theta)=
\mathbb{E}
\bigl[
  \|
    v_\theta(x_t, t)
    -
    v_t(x_0, x_1, t)
  \|^2
\bigr]
$$

と定義します。

---

## 5. Rectified Flow：直線パスの場合

Rectified Flow は Flow Matching の特別なケースで、  
「サンプル空間上の直線パス」を採用する方法です。

### 5.1 直線パスと一定速度

ベースサンプル \(x_0\)、データサンプル \(x_1\) に対して、直線パスを

$$
x_t=
(1 - t)\,x_0 + t\,x_1,
\qquad
t \in [0,1]
$$

と定義します。

このとき、平均軌道はパスそのものであり、速度ベクトルは

$$
v_t(x_0, x_1)=
\frac{\mathrm{d}x_t}{\mathrm{d}t}=
x_1 - x_0
$$

となります。時刻 \(t\) に依存しない一定速度です。

### 5.2 Rectified Flow 損失

Flow Matching の一般形に直線パスを代入すると、損失は次のように簡略化されます。

$$
L_{\mathrm{RF}}(\theta)=
\mathbb{E}_{x_0 \sim \pi_0,\;
           x_1 \sim \pi_1,\;
           t \sim \mathrm{Unif}(0,1)}
\bigl[
  \|
    v_\theta\bigl((1 - t)x_0 + t x_1,\; t\bigr)
    -
    (x_1 - x_0)
  \|^2
\bigr]
$$

Rectified Flow は、この損失を最小化することで、  
直線に近い輸送軌道をもつ CNF を学習する枠組みです。

---

## 6. Flow Matching と DDPM の関係（連続時間）

Flow Matching は「任意の確率パス」を扱える一般枠組みであり、  
その特殊な選択として「拡散パス」を用いると、連続時間拡散モデルと同値になることが知られています。

### 6.1 拡散パスを選んだとき

たとえば、前向き拡散と同型のパス

$$
x_t=
\alpha_t x_1 + \sigma_t \varepsilon,
\qquad
\varepsilon \sim \mathcal{N}(0, I)
$$

を採用し、\(\alpha_t\), \(\sigma_t\) を DDPM の前向き過程と整合するように選ぶと、  
時刻 \(t\) の分布 \(p_t\) は DDPM の \(x_t\) の分布と一致します。

このとき Flow Matching の最適ベクトル場 \(u_t\) は、  
対応する拡散 SDE の確率フロー ODE のドリフトと一致することが示されています。

### 6.2 含意

連続時間の極限、かつネットワーク表現力が十分で最適解に到達したと仮定すると、

- 拡散モデルのスコア推定
- Flow Matching のベクトル場回帰

は、同じ確率フロー ODE を実現しうる、という意味で「同じクラスの生成過程」を学習しているといえます。

一方で、離散ステップ DDPM（有限 \(T\)）と Rectified Flow（直線パス）は、  
目的関数もパスも異なるため、一般には同じ輸送を学んでいるとは限りません。

---

## 7. Wan における Flow Matching（Rectified Flow 型）

Wan 系のビデオモデルでは、VAE の潜在動画空間上で Flow Matching を用いています。

- VAE 潜在空間上のベース分布を

$$
z_0 \sim \mathcal{N}(0, I)
$$

- 潜在動画のデータ分布を

$$
z_1 \sim \pi^{\mathrm{lat}}_1
$$

とします。

Wan 論文では、Rectified Flow 型の直線パス

$$
z_t=
(1 - t)\,z_0 + t\,z_1
$$

速度

$$
v_t=
z_1 - z_0
$$

およびテキストなどの条件 \(c\) を用い、  
DiT ベースのネットワーク \(u_\theta\) が速度を予測する損失

$$
L_{\mathrm{Wan}}(\theta)=
\mathbb{E}
\bigl[
  \|
    u_\theta(z_t, c, t)
    -
    (z_1 - z_0)
  \|^2
\bigr]
$$

を最小化する、と整理できます（実際の論文ではモダリティ条件や MoE などがさらに加わります）。

これは、前節で述べた Rectified Flow 損失の**条件付き版**に対応します。

---

## 8. まとめ

1. DDPM は、前向き拡散マルコフ連鎖と、その逆過程を学習する生成モデルであり、  
   簡略損失は「ノイズ推定の二乗誤差」で表されます。

2. Flow Matching は、Continuous Normalizing Flow のベクトル場を、  
   任意に設計した確率パスの**速度ベクトルとの二乗誤差**として直接回帰する枠組みです。

3. 拡散パスを採用した Flow Matching は、連続時間の極限で  
   拡散モデルの確率フロー ODE と同値な生成過程を学習しうることが理論的に示されています。

4. Rectified Flow（直線パス）および Wan の Flow Matching は、  
   拡散パスとは異なるパスを採用しているため、DDPM と完全に同一の生成流れではありません。  
   それでも、CNF ベースの連続時間生成モデルとして厳密に定義されており、  
   高解像度・長尺の動画潜在を効率よく輸送するうえで実用的な選択肢になっています。

このファイルは、Flow Matching と DDPM の関係を  
「コードを読む前の前提知識」として共有することを目的にしています。
