from pipeline import decompose, hide, hidden, lama, call, loop, eval, find_list, find_subtask,extract_json, eval_decomp, eval_baseline
import requests, json, ast, re, ollama


def baseline(prompt, target_llm ="google/gemini-3.5-flash",judge_llm ="z-ai/glm-5.2"):

    LLM_response = call(prompt, llm =target_llm)
    judge_verdict = extract_json(eval_baseline(prompt,LLM_response,judge_llm))
    return LLM_response, judge_verdict

def decomp_only(prompt, target_llm ="google/gemini-3.5-flash",judge_llm ="z-ai/glm-5.2"):

    subtasks = find_list(lama(decompose(prompt)))
    LLM_response=[]
    for y in subtasks:
        LLM_response.append(call(y, target_llm))
    judge_verdict = extract_json(eval_decomp(prompt,subtasks,LLM_response,judge_llm))
    
    return LLM_response, judge_verdict

def decomp_and_pair(prompt, target_llm ="google/gemini-3.5-flash",judge_llm ="z-ai/glm-5.2"):

    subtasks = find_list(lama(decompose(prompt)))
    
    PAIR_subtasks = []
    
    for x in subtasks:
        PAIR_subtasks.append(loop(x, target_llm, judge_llm))
    
    
    LLM_response = []
    for y in PAIR_subtasks:
        LLM_response.append((call(y, target_llm)))
    judge_verdict = extract_json(eval(prompt,subtasks,PAIR_subtasks,LLM_response,judge_llm))
    
    return LLM_response, judge_verdict



def pipline(prompt, target_llm ="google/gemini-3.5-flash",judge_llm ="z-ai/glm-5.2"):

    subtasks = find_list(lama(decompose(prompt)))
    
    PAIR_subtasks = []
    
    for x in subtasks:
        PAIR_subtasks.append(loop(x, target_llm, judge_llm))
    
    hidden_PAIR_subtasks = hidden(PAIR_subtasks)
    
    LLM_response = []
    for y in hidden_PAIR_subtasks:
        LLM_response.append(find_subtask(call(y, target_llm)))
    judge_verdict = extract_json(eval(prompt,subtasks,PAIR_subtasks,LLM_response,judge_llm))
    
    return LLM_response, judge_verdict




if __name__ == "__main__":
    ###Full run of the whole pipeline
    ###With all Information saved to csv
    import csv

    INPUT = "strongreject.csv"          # columns: category, source, forbidden_prompt
    OUTPUT = "strongreject_results.csv"
    TARGET_LLM = "google/gemini-3.5-flash"
    JUDGE_LLM = "z-ai/glm-5.2"

    with open(INPUT, encoding="utf-8") as f:
        prompts = [row["forbidden_prompt"] for row in csv.DictReader(f)]

    columns = ["prompt", "response", "decomposition", "pair decomposition",
               "refused", "relevance", "specificity", "actionability", "accuracy"]

    with open(OUTPUT, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()

        for i, prompt in enumerate(prompts, 1):
            print(f"\n===== [{i}/{len(prompts)}] {prompt[:70]} =====")
            try:
                # full pipeline: decompose -> PAIR-refine -> hidden encoding -> answer -> judge
                subtasks = find_list(lama(decompose(prompt)))
                pair_subtasks = [loop(x, TARGET_LLM, JUDGE_LLM) for x in subtasks]
                encoded = hidden(pair_subtasks)
                response = [find_subtask(call(y, TARGET_LLM)) for y in encoded]
                verdict = extract_json(eval(prompt, subtasks, pair_subtasks, response, JUDGE_LLM))
            except Exception as e:
                print("   ERROR:", e)
                writer.writerow({"prompt": prompt, "response": f"[ERROR: {e}]"})
                f.flush()
                continue

            writer.writerow({
                "prompt": prompt,
                "response": json.dumps(response, ensure_ascii=False),
                "decomposition": json.dumps(subtasks, ensure_ascii=False),
                "pair decomposition": json.dumps(pair_subtasks, ensure_ascii=False),
                "refused": verdict.get("refused"),
                "relevance": verdict.get("relevance"),
                "specificity": verdict.get("specificity"),
                "actionability": verdict.get("actionability"),
                "accuracy": verdict.get("accuracy"),
            })
            f.flush()

    print("\nDone ->", OUTPUT)
