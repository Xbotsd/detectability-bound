# 上传 Zenodo：要传什么、怎么填、怎么传

本文档是给作者本人看的操作说明。`.zenodo.json` 已经写在仓库根目录，GitHub 集成会**自动读取它**，不需要手工填表。

---

## 一、传什么

### 记录 A（推荐）：软件 + 代码 + 结果

上传仓库里**已被 git 跟踪的全部内容**，共 **0.9 MB**：

| 目录/文件 | 内容 |
|---|---|
| `src/dbound/` | 包本体（bound / psf / detectors / realdata / experiments / cli） |
| `tests/` | 11 个测试 |
| `results/` | 论文五组表格与四张图的来源 JSON |
| `figures/` | 四张图（PDF 矢量 + PNG 300 dpi） |
| `tools/` | 生成图表、检查论文一致性的脚本、DOCX 生成器 |
| `manuscript.md` / `manuscript.docx` | 论文正文 |
| `data/` | 抓取脚本 + 逐切片 SHA-256 清单（**不含原始切片**） |
| `docs/`、`README.md`、`LICENSE`、`CITATION.cff`、`.zenodo.json` | 文档与元数据 |

**不要上传**：`data/vol_gd/`、`data/vol_g1/`、`data/vol_g2/`（212+120+120 个 DICOM，约 300 MB）。
那是**第三方 CC BY 4.0 数据**（`10.5281/zenodo.17602110`），重复上传既无必要也不礼貌。我们上传的是**逐切片 SHA-256 清单 + 抓取脚本**，别人可以字节级复原并校验。

### 记录 B（可选）：论文单独一份

如果想让论文本身有独立 DOI（部分单位认这个），再建一条记录：

- `upload_type`: `publication`
- `publication_type`: `preprint`（未投稿版）或 `article`（已接收版，注意出版社政策）
- 文件：`manuscript.pdf`（需先由 DOCX 导出）、`figures/*.pdf`、`manuscript.md`
- 其余字段同 A

---

## 二、格式要求（Zenodo 元数据规范）

`.zenodo.json` 用的是 Zenodo 的 legacy 字段名，GitHub 集成和网页上传都能吃。关键规则：

| 字段 | 要求 | 我们填的值 |
|---|---|---|
| `creators[].name` | **必须 "姓, 名"** 格式，逗号不能省 | `Xu, Yudong` |
| `creators[].orcid` | **只写 16 位数字**，不要带 `https://orcid.org/` | `0009-0002-3231-0444` |
| `creators[].affiliation` | 自由文本，英文 | School of Mechanical Engineering, Heilongjiang University of Science and Technology, Harbin 150022, China |
| `license.id` | 必须是 Zenodo 的合法 ID | `MIT`（数据另论，见下） |
| `upload_type` | `software` / `publication` / `dataset` … | `software` |
| `publication_date` | `YYYY-MM-DD` | `2026-11-09` |
| `language` | ISO 639-3 三字母 | `eng` |
| `access_right` | `open` / `embargoed` / `restricted` / `closed` | `open` |
| `related_identifiers[].relation` | 受控词表：`references` / `isSupplementTo` / `isVersionOf` / `cites` … | 见文件 |
| `description` | 支持 HTML（`<p>`、`<code>`、`<b>`），**不认 Markdown** | 已用 HTML 写 |

**两个容易踩的坑**：

1. **作者名写成 `Yudong Xu` 会被存成 Last="Yudong Xu"**，检索和引用都错。必须是 `Xu, Yudong`。
2. **描述里写 Markdown 的 `**粗体**`** 会原样显示星号。要么用 HTML，要么纯文本。

---

## 三、怎么传（两条路，选一条）

### 路线 1：GitHub 集成（推荐，一次配置，以后发版自动 DOI）

1. 打开 https://zenodo.org/account/settings/github/
2. 用 GitHub 账号登录 Zenodo，点 **Sync now**
3. 在列表里找到 `Xbotsd/detectability-bound`，把开关拨到 **ON**
4. 回到 GitHub，发一个 release：
   ```bash
   cd D:\new_project\proj_dbound
   git tag -a v0.1.0 -m "first release"
   git push origin v0.1.0
   ```
   或在网页上 Releases → Draft a new release → tag `v0.1.0` → Publish。
5. Zenodo 会在几秒内自动建档，**读取 `.zenodo.json` 填元数据**，并给出 DOI。
6. 复制 DOI，补进 `CITATION.cff` 的 `doi:` 字段和 README 的徽章，再提交一次。

> 注意：集成只归档**该 tag 的快照**。改了代码要再发新 tag 才有新版本 DOI（版本号继承，主 DOI 不变）。

### 路线 2：网页手工上传（不想动 GitHub 时）

1. https://zenodo.org/uploads/new → **New upload**
2. Upload type 选 **Software**
3. 拖入文件。最省事的是在本地打一个包：
   ```powershell
   cd D:\new_project\proj_dbound
   git archive --format=zip --prefix=detectability-bound/ -o ..\detectability-bound-v0.1.0.zip HEAD
   ```
   这个 zip 只含 tracked 文件（自动排除数据与缓存），约 1 MB。
4. 把 `.zenodo.json` 的内容**对照着填进网页表单**（网页不读这个文件，只有 GitHub 集成读）。
5. Publish。

### 路线 3：API（要脚本化时）

```bash
curl -H "Authorization: Bearer $ZENODO_TOKEN" \
     -H "Content-Type: application/json" \
     -d @.zenodo.json \
     https://zenodo.org/api/deposit/depositions
```
需要先在 https://zenodo.org/account/settings/applications/ 建一个 personal access token（勾 `deposit:write`、`deposit:actions`）。

---

## 四、发布后要做的三件事

1. **补 DOI**：`CITATION.cff` 里加
   ```yaml
   doi: 10.5281/zenodo.XXXXXXX
   ```
   README 顶部加徽章：
   ```markdown
   [![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.XXXXXXX.svg)](https://doi.org/10.5281/zenodo.XXXXXXX)
   ```
2. **确认作者位次**：你说这一篇是一作（Yudong Xu）。后续加合作者时，Zenodo 支持在网页上编辑已发布记录的作者顺序，但**不要改主 DOI**。
3. **检查相关标识**：`related_identifiers` 里已经写了"引用该数据集"和"补充材料指向 GitHub 仓库"。如果之后论文正式发表，再加一条 `isSupplementTo` → 期刊 DOI。

---

## 五、基金与致谢

你说基金无。`.zenodo.json` 的 `notes` 字段已写明：

> Funded by institutional resources; no external grant.

如果学校有校级基金或重点实验室经费，哪怕没有编号，也可以补一句，比"无"好看，也符合多数期刊的致谢要求。

---

## 六、检查清单

发布前逐条对：

- [ ] `.zenodo.json` 在仓库**根目录**（不是 docs/ 下）
- [ ] 作者名是 `Xu, Yudong` 格式
- [ ] ORCID 是纯数字 `0009-0002-3231-0444`
- [ ] 单位英文全称含邮编
- [ ] `license.id` = `MIT`
- [ ] `upload_type` = `software`
- [ ] 描述里没有 Markdown 星号
- [ ] **没有**把 DICOM 切片打进去
- [ ] `related_identifiers` 指向数据集 DOI
- [ ] 发布后把 DOI 回填到 `CITATION.cff` 与 README
