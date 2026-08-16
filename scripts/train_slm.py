#!/usr/bin/env python3
"""Entraine l'eleve sur le jeu assemble. A executer sur la station GPU.

Deux choix s'ecartent du benchmark de juillet, et il faut dire pourquoi.

**Fine-tuning complet plutot que QLoRA.** Le benchmark prevoyait QLoRA rang 8 en
4 bits, ce qui correspondait a une hypothese de VRAM modeste. Sur une A5000 de
24 Go, un modele de 0,8 milliard de parametres tient largement en entrainement
complet : 1,6 Go de poids, autant de gradients, 6,4 Go d'etats Adam, plus les
activations — de l'ordre de 15 Go. Un adaptateur de rang 8 brideraut la capacite
sans necessite. QLoRA reste accessible par `--methode qlora` si la mesure montre
que le complet sur-apprend.

**Perte calculee sur la seule reponse.** Le texte d'entrainement contient le
contexte, le commentaire, puis la cible. Sans masquage, le modele apprendrait
aussi a generer des commentaires algeriens — ce qui n'est pas la tache, consomme
de la capacite et fausse la perte de validation. Le masque coupe au marqueur de
reponse, qui differe selon la vue entrainee.

Le benchmark exige au moins deux graines par configuration : un ecart entre deux
graines dit ce qu'une mesure unique ne peut pas dire.

Usage, sur la station :
  python train_slm.py --data sft_trace_json --sortie runs/trace_s1 --seed 1
  python train_slm.py --data sft_json_only  --sortie runs/json_s1  --seed 1
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

#: Le masque de perte commence apres ce marqueur. La vue avec trace apprend le
#: raisonnement ET l'annotation ; la vue d'ablation n'apprend que l'annotation.
MARQUEURS = {
    'sft_trace_json': '### Raisonnement ###',
    'sft_json_only': '### Annotation ###',
}


def charger(chemin: Path) -> list[str]:
    return [json.loads(l)['text'] for l in chemin.read_text(encoding='utf-8').splitlines()
            if l.strip()]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--data', default='sft_trace_json', choices=sorted(MARQUEURS))
    ap.add_argument('--racine', default='data/processed/slm_v2_sft')
    ap.add_argument('--modele', default='Qwen/Qwen3.5-0.8B')
    ap.add_argument('--sortie', required=True)
    ap.add_argument('--methode', default='complet', choices=('complet', 'qlora'))
    ap.add_argument('--epochs', type=float, default=3)
    ap.add_argument('--lr', type=float, default=1e-5)
    ap.add_argument('--batch', type=int, default=4)
    ap.add_argument('--accum', type=int, default=4)
    ap.add_argument('--cutoff', type=int, default=1024)
    ap.add_argument('--seed', type=int, default=1)
    args = ap.parse_args()

    import torch
    from datasets import Dataset
    from transformers import (AutoModelForCausalLM, AutoTokenizer,
                              DataCollatorForSeq2Seq, Trainer, TrainingArguments,
                              set_seed)

    set_seed(args.seed)
    racine = Path(args.racine)
    marqueur = MARQUEURS[args.data]
    tok = AutoTokenizer.from_pretrained(args.modele)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token

    def encoder(exemples):
        """Tokenise et masque tout ce qui precede la reponse."""
        entrees, etiquettes = [], []
        for texte in exemples['texte']:
            coupe = texte.find(marqueur)
            if coupe < 0:
                continue
            invite, reponse = texte[:coupe], texte[coupe:]
            ids_invite = tok(invite, add_special_tokens=False)['input_ids']
            ids_reponse = tok(reponse, add_special_tokens=False)['input_ids'] + [tok.eos_token_id]
            ids = (ids_invite + ids_reponse)[:args.cutoff]
            # -100 = position ignoree par la perte.
            masque = ([-100] * len(ids_invite) + ids_reponse)[:args.cutoff]
            entrees.append(ids)
            etiquettes.append(masque)
        return {'input_ids': entrees, 'labels': etiquettes,
                'attention_mask': [[1] * len(x) for x in entrees]}

    jeux = {}
    for split in ('train', 'dev'):
        textes = charger(racine / f'{args.data}_{split}.jsonl')
        jeux[split] = Dataset.from_dict({'texte': textes}).map(
            encoder, batched=True, remove_columns=['texte'])
        print(f'{split:5s} {len(jeux[split])} exemples')

    charge = {'torch_dtype': torch.bfloat16, 'device_map': 'auto'}
    if args.methode == 'qlora':
        from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
        from transformers import BitsAndBytesConfig
        charge['quantization_config'] = BitsAndBytesConfig(
            load_in_4bit=True, bnb_4bit_quant_type='nf4',
            bnb_4bit_compute_dtype=torch.bfloat16, bnb_4bit_use_double_quant=True)
    modele = AutoModelForCausalLM.from_pretrained(args.modele, **charge)
    if args.methode == 'qlora':
        modele = prepare_model_for_kbit_training(modele)
        modele = get_peft_model(modele, LoraConfig(
            r=8, lora_alpha=16, lora_dropout=0.05, task_type='CAUSAL_LM',
            target_modules=['q_proj', 'k_proj', 'v_proj', 'o_proj',
                            'gate_proj', 'up_proj', 'down_proj']))
        modele.print_trainable_parameters()
    modele.config.use_cache = False

    Trainer(
        model=modele,
        args=TrainingArguments(
            output_dir=args.sortie,
            num_train_epochs=args.epochs,
            per_device_train_batch_size=args.batch,
            gradient_accumulation_steps=args.accum,
            learning_rate=args.lr,
            lr_scheduler_type='cosine',
            warmup_ratio=0.03,
            bf16=True,
            gradient_checkpointing=True,
            logging_steps=25,
            eval_strategy='steps',
            eval_steps=200,
            save_strategy='steps',
            save_steps=200,
            save_total_limit=2,
            load_best_model_at_end=True,
            metric_for_best_model='eval_loss',
            seed=args.seed,
            report_to=[],
        ),
        train_dataset=jeux['train'],
        eval_dataset=jeux['dev'],
        data_collator=DataCollatorForSeq2Seq(tok, padding=True, label_pad_token_id=-100),
    ).train()

    modele.save_pretrained(args.sortie)
    tok.save_pretrained(args.sortie)
    (Path(args.sortie) / 'configuration.json').write_text(json.dumps({
        'vue': args.data, 'modele_base': args.modele, 'methode': args.methode,
        'epochs': args.epochs, 'lr': args.lr, 'batch': args.batch,
        'accum': args.accum, 'cutoff': args.cutoff, 'seed': args.seed,
        'marqueur_de_perte': marqueur,
    }, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f'\nmodele ecrit dans {args.sortie}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
