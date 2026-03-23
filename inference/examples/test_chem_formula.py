"""
化学分子式识别 Benchmark 测试脚本

此脚本用于测试 ChemFormulaRecognition 数据集类的功能
"""

import sys
from pathlib import Path

# 添加项目路径
sys.path.append(str(Path(__file__).parent.parent))

from vlmeval.dataset import ChemFormulaRecognition
import pandas as pd


def test_normalize_formula():
    """测试分子式标准化函数"""
    from vlmeval.dataset.chem_formula import normalize_formula
    
    print("=" * 60)
    print("测试 normalize_formula 函数")
    print("=" * 60)
    
    test_cases = [
        ("H2O", "H2O"),
        ("  H2O  ", "H2O"),
        ("C 6 H 12 O 6", "C 6 H 12 O 6"),
        ("", ""),
    ]
    
    for input_val, expected in test_cases:
        result = normalize_formula(input_val)
        status = "✓" if result == expected else "✗"
        print(f"{status} Input: '{input_val}' -> Output: '{result}' (Expected: '{expected}')")
    print()


def test_exact_match():
    """测试精确匹配评分"""
    from vlmeval.dataset.chem_formula import exact_match_score
    
    print("=" * 60)
    print("测试 exact_match_score 函数")
    print("=" * 60)
    
    test_cases = [
        ("H2O", "H2O", 1),
        ("H2o", "H2O", 0),
        ("C6H12O6", "C6H12O6", 1),
        ("CH3COOH", "CH3COH", 0),
    ]
    
    for pred, ans, expected in test_cases:
        result = exact_match_score(pred, ans)
        status = "✓" if result == expected else "✗"
        print(f"{status} Pred: '{pred}', Ans: '{ans}' -> Score: {result} (Expected: {expected})")
    print()


def test_case_insensitive_match():
    """测试不区分大小写的匹配"""
    from vlmeval.dataset.chem_formula import case_insensitive_match_score
    
    print("=" * 60)
    print("测试 case_insensitive_match_score 函数")
    print("=" * 60)
    
    test_cases = [
        ("H2O", "h2o", 1),
        ("C6H12O6", "c6h12o6", 1),
        ("CH3COOH", "CH3COH", 0),
    ]
    
    for pred, ans, expected in test_cases:
        result = case_insensitive_match_score(pred, ans)
        status = "✓" if result == expected else "✗"
        print(f"{status} Pred: '{pred}', Ans: '{ans}' -> Score: {result} (Expected: {expected})")
    print()


def test_similarity():
    """测试相似度计算"""
    from vlmeval.dataset.chem_formula import calculate_formula_similarity
    
    print("=" * 60)
    print("测试 calculate_formula_similarity 函数")
    print("=" * 60)
    
    test_cases = [
        ("H2O", "H2O", 1.0),
        ("H2O", "H2O2", 0.75),  # 编辑距离为1，最大长度4
        ("C6H12O6", "C6H12O5", 0.875),  # 编辑距离为1，最大长度8
    ]
    
    for pred, ans, expected_min in test_cases:
        result = calculate_formula_similarity(pred, ans)
        status = "✓" if result >= expected_min - 0.05 else "✗"
        print(f"{status} Pred: '{pred}', Ans: '{ans}' -> Similarity: {result:.3f} (Expected: >={expected_min})")
    print()


def test_dataset_structure():
    """测试数据集结构"""
    print("=" * 60)
    print("测试数据集类结构")
    print("=" * 60)
    
    # 检查数据集类是否正确定义
    print("✓ ChemFormulaRecognition 类已正确导入")
    print(f"  - TYPE: {ChemFormulaRecognition.TYPE}")
    print(f"  - DATASET_URL: {ChemFormulaRecognition.DATASET_URL}")
    print(f"  - DATASET_MD5: {ChemFormulaRecognition.DATASET_MD5}")
    
    # 检查子类
    from vlmeval.dataset import (
        ChemFormulaRecognitionOrganic,
        ChemFormulaRecognitionInorganic,
        ChemFormulaRecognitionStructural
    )
    
    print("\n子类:")
    print("  ✓ ChemFormulaRecognitionOrganic")
    print("  ✓ ChemFormulaRecognitionInorganic")
    print("  ✓ ChemFormulaRecognitionStructural")
    print()


def test_evaluation_metrics():
    """测试评估指标计算"""
    print("=" * 60)
    print("测试评估指标计算")
    print("=" * 60)
    
    # 创建模拟数据
    data = pd.DataFrame({
        'index': [0, 1, 2, 3, 4],
        'question': ['识别分子式'] * 5,
        'answer': ['H2O', 'C6H12O6', 'CH3COOH', 'NaCl', 'O2'],
        'prediction': ['H2O', 'C6H12O6', 'CH3COH', 'Nacl', 'O2'],
        'category': ['inorganic', 'organic', 'organic', 'inorganic', 'inorganic'],
        'difficulty': ['easy', 'medium', 'medium', 'easy', 'easy']
    })
    
    # 手动计算指标
    from vlmeval.dataset.chem_formula import (
        exact_match_score,
        case_insensitive_match_score,
        calculate_formula_similarity
    )
    
    exact_matches = sum(
        exact_match_score(pred, ans)
        for pred, ans in zip(data['prediction'], data['answer'])
    )
    
    case_insensitive_matches = sum(
        case_insensitive_match_score(pred, ans)
        for pred, ans in zip(data['prediction'], data['answer'])
    )
    
    print(f"精确匹配: {exact_matches}/{len(data)} = {exact_matches/len(data)*100:.1f}%")
    print(f"不区分大小写匹配: {case_insensitive_matches}/{len(data)} = {case_insensitive_matches/len(data)*100:.1f}%")
    
    # 分类别统计
    print("\n分类别统计:")
    for cat in data['category'].unique():
        cat_data = data[data['category'] == cat]
        cat_exact = sum(
            exact_match_score(pred, ans)
            for pred, ans in zip(cat_data['prediction'], cat_data['answer'])
        )
        print(f"  {cat}: {cat_exact}/{len(cat_data)} = {cat_exact/len(cat_data)*100:.1f}%")
    
    print()


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("化学分子式识别 Benchmark 功能测试")
    print("=" * 60 + "\n")
    
    try:
        test_normalize_formula()
        test_exact_match()
        test_case_insensitive_match()
        test_similarity()
        test_dataset_structure()
        test_evaluation_metrics()
        
        print("=" * 60)
        print("✓ 所有测试完成！")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()

