"""Tests for factor calculation consistency between training and prediction"""

import pytest
from keiba.analyzers.factors import TimeIndexFactor, Last3FFactor, PedigreeFactor, RunningStyleFactor


def test_training_service_passes_track_condition_to_time_index_factor():
    """training_serviceがTimeIndexFactorにtrack_conditionを渡すことを検証"""
    # この整合性は、training_serviceがtrack_conditionをtime_indexファクターに
    # 渡すことで保証される。現在は渡していないため、このテストは
    # 実装後にパスするようになる。

    # テスト戦略: training_service.pyの実装を直接確認することで検証
    import inspect
    from keiba.services import training_service

    source = inspect.getsource(training_service.build_training_data)

    # track_conditionがtime_indexの呼び出しに含まれることを確認
    # 現在は含まれていないため、このテストは失敗するはず
    assert "track_condition" in source, (
        "training_service.build_training_data()にtrack_conditionの記述が見つからない"
    )

    # より具体的に、time_indexの呼び出し箇所でtrack_conditionが渡されることを確認
    lines = source.split("\n")
    time_index_section = []
    in_time_index = False

    for line in lines:
        if '"time_index"' in line and "factors[" in line:
            in_time_index = True
        if in_time_index:
            time_index_section.append(line)
            if ")," in line:  # calculate呼び出しの終わり
                break

    time_index_code = "\n".join(time_index_section)

    # track_conditionが渡されていることを確認（現在は失敗するはず）
    assert "track_condition" in time_index_code, (
        f"time_indexファクターの呼び出しにtrack_conditionが含まれていない:\n{time_index_code}"
    )


def test_training_service_passes_surface_and_track_condition_to_last_3f_factor():
    """training_serviceがLast3FFactorにsurfaceとtrack_conditionを渡すことを検証"""
    import inspect
    from keiba.services import training_service

    source = inspect.getsource(training_service.build_training_data)
    lines = source.split("\n")
    last_3f_section = []
    in_last_3f = False

    for line in lines:
        if '"last_3f"' in line and "factors[" in line:
            in_last_3f = True
        if in_last_3f:
            last_3f_section.append(line)
            if ")," in line:
                break

    last_3f_code = "\n".join(last_3f_section)

    # surfaceとtrack_conditionが渡されていることを確認（現在は失敗するはず）
    assert "surface" in last_3f_code, (
        f"last_3fファクターの呼び出しにsurfaceが含まれていない:\n{last_3f_code}"
    )
    assert "track_condition" in last_3f_code, (
        f"last_3fファクターの呼び出しにtrack_conditionが含まれていない:\n{last_3f_code}"
    )


def test_training_service_uses_distance_and_track_condition_for_pedigree_factor():
    """training_serviceがPedigreeFactorにdistanceとtrack_conditionを渡すことを検証"""
    import inspect
    from keiba.services import training_service

    source = inspect.getsource(training_service.build_training_data)
    lines = source.split("\n")
    pedigree_section = []
    in_pedigree = False

    for line in lines:
        if '"pedigree"' in line and "factors[" in line:
            in_pedigree = True
        if in_pedigree:
            pedigree_section.append(line)
            if ")," in line:
                break

    pedigree_code = "\n".join(pedigree_section)

    # distance（target_distanceではない）とtrack_conditionが渡されていることを確認
    assert "distance=" in pedigree_code, (
        f"pedigreeファクターの呼び出しにdistance=が含まれていない:\n{pedigree_code}"
    )
    assert "track_condition=" in pedigree_code, (
        f"pedigreeファクターの呼び出しにtrack_condition=が含まれていない:\n{pedigree_code}"
    )
    # target_surfaceやtarget_distanceは使わないことを確認
    assert "target_surface" not in pedigree_code, (
        f"pedigreeファクターの呼び出しにtarget_surfaceが含まれている（distanceを使うべき）:\n{pedigree_code}"
    )
    assert "target_distance" not in pedigree_code, (
        f"pedigreeファクターの呼び出しにtarget_distanceが含まれている（distanceを使うべき）:\n{pedigree_code}"
    )


def test_training_service_uses_target_distance_for_running_style_factor():
    """training_serviceがRunningStyleFactorにtarget_distanceを渡すことを検証"""
    import inspect
    from keiba.services import training_service

    source = inspect.getsource(training_service.build_training_data)
    lines = source.split("\n")
    running_style_section = []
    in_running_style = False

    for line in lines:
        if '"running_style"' in line and "factors[" in line:
            in_running_style = True
        if in_running_style:
            running_style_section.append(line)
            if ")," in line:
                break

    running_style_code = "\n".join(running_style_section)

    # target_distanceが渡されていることを確認
    assert "target_distance=" in running_style_code, (
        f"running_styleファクターの呼び出しにtarget_distance=が含まれていない:\n{running_style_code}"
    )
    # passing_order, course, distanceは使わないことを確認
    assert "passing_order=" not in running_style_code, (
        f"running_styleファクターの呼び出しにpassing_order=が含まれている（不要）:\n{running_style_code}"
    )
    assert "course=" not in running_style_code, (
        f"running_styleファクターの呼び出しにcourse=が含まれている（不要）:\n{running_style_code}"
    )
    # distance=は使わない（target_distance=を使う）
    assert "distance=" not in running_style_code or "target_distance=" in running_style_code, (
        f"running_styleファクターの呼び出しにdistance=が含まれている（target_distance=を使うべき）:\n{running_style_code}"
    )
