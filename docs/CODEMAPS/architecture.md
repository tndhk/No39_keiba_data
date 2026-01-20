# Architecture Codemap

> Freshness: 2026-01-20T23:00:00+09:00

## System Overview

```
keiba/                    # 競馬データ収集・分析CLI
├── cli.py               # CLIエントリーポイント (Click)
├── db.py                # DB接続・セッション管理
├── constants.py         # 定数定義
├── models/              # SQLAlchemy ORM
├── scrapers/            # Webスクレイパー
├── analyzers/           # レース分析エンジン
│   └── factors/         # スコア算出因子 (7種)
├── ml/                  # ML予測モジュール
├── config/              # 設定・マスタデータ
└── utils/               # ユーティリティ
```

## Module Dependencies

```
cli.py
├── db.py (get_engine, get_session, init_db)
├── models/ (Horse, Jockey, Race, RaceResult, Trainer)
├── scrapers/ (HorseDetailScraper, RaceDetailScraper, RaceListScraper)
├── analyzers/factors/ (7 factors)
├── analyzers/score_calculator.py
├── ml/ (FeatureBuilder, Trainer, Predictor)
└── utils/grade_extractor.py

analyzers/score_calculator.py
└── config/weights.py (FACTOR_WEIGHTS)

ml/trainer.py
├── lightgbm (LGBMClassifier)
└── sklearn (StratifiedKFold, metrics)

ml/predictor.py
└── lightgbm (LGBMClassifier)

ml/feature_builder.py
└── (pure Python, no external deps)
```

## Data Flow

```
[netkeiba.com]
    ↓ scrapers/
[SQLite DB]
    ↓ models/
[Race/Horse Data]
    ↓ analyzers/factors/
[Factor Scores (7種)]
    ↓ ml/feature_builder
[Features (19種)]
    ↓ ml/trainer → ml/predictor
[Top-3 Probability]
    ↓ cli.py
[Output: Score Table + ML Prediction]
```

## CLI Commands

| Command | Handler | Description |
|---------|---------|-------------|
| `scrape` | `cli.scrape()` | 年月指定でレースデータ収集 |
| `scrape-horses` | `cli.scrape_horses()` | 馬詳細データ収集 |
| `analyze` | `cli.analyze()` | レース分析 + ML予測 |
| `migrate-grades` | `cli.migrate_grades()` | グレード情報マイグレーション |

## External Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| sqlalchemy | >=2.0 | ORM |
| requests | >=2.28 | HTTP |
| beautifulsoup4 | >=4.11 | HTML Parser |
| lxml | >=4.9 | XML/HTML |
| click | >=8.0 | CLI |
| lightgbm | >=4.0.0 | ML (Gradient Boosting) |
| scikit-learn | >=1.3.0 | ML Utilities |
