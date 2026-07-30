# Validation humaine — gold V0.3

60 commentaires a relire. Compte environ 45 minutes.

Pour chaque item : le texte, puis **une** annotation produite par le systeme.
Dis simplement si elle est correcte. Tu ne sais pas — volontairement — si les
deux annotateurs automatiques etaient d accord sur cet item. C est ce qui permet
de detecter une erreur qu ils partagent tous les deux.

Ne cherche pas la perfection : juge si un responsable metier accepterait cette
annotation telle quelle.

Reference des valeurs autorisees :
`data/processed/slm_v2_gold/campaign_v0.2/VOCABULAIRES_FERMES_V0.2.md`

---

## 1. `v02_0252`

```text
اللهم صلي على محمد وعلى آله محمد كما صليتا على إبراهيم وعلى آله إبراهيم إنك حميد مجيد 🤍🤍🤍اللهم صلي على محمد وعلى آله محمد كما صليتا على إبراهيم وعلى آله إبراهيم إنك حميد مجيد 🤍🤍🤍اللهم صلي على محمد وعلى آله محمد كما صليتا على إبراهيم وعلى آله إبراهيم إنك حميد مجيد 🤍🤍🤍اللهم صلي على محمد وعلى آله محمد كما صليتا على إبراهيم وعلى آله إبراهيم إنك حميد مج
[… tronque, 2101 caracteres au total, contenu repetitif]
```

- Cible surveillée : **organisation — Hamoud Boualem**
- Auteur : **consommateur**
- Exploitable : **False** (spam)
- Pertinence business : **aucune**
- Langue : **arabe_msa**
- Sentiment : **neutre** / faible / aucune
  - preuves : —
- Intentions : **—**
- Aspects : **—**
- Alertes : **—**

**Verdict** — remplace une seule case par `x` :

- x correcte
- [ ] acceptable, nuance discutable
- [ ] INCORRECTE

Si incorrecte, dis en une ligne ce qui devrait changer :

> 

---

## 2. `v02_0125`

```text
زايدة نصيرة في شهر سبتمبر Ramy Food L'alge Rienne Ansem Insaf Baghdad Nadji Alger Alger سميرة سمورة
```

- Cible surveillée : **organisation — Ramy**
- Auteur : **consommateur**
- Exploitable : **True**
- Pertinence business : **directe**
- Langue : **darija_arabe**
- Sentiment : **neutre** / faible / aucune
  - preuves : —
- Intentions : **tag_mention**
- Aspects : **—**
- Alertes : **—**

**Verdict** — remplace une seule case par `x` :

- x correcte
- [ ] acceptable, nuance discutable
- [ ] INCORRECTE

Si incorrecte, dis en une ligne ce qui devrait changer :

> 

---

## 3. `v02_0277`

```text
بسم الله أشارك شهر سبتمبر Yassine chopPacĥïka ĐżDjllouLi Abdelmalk
```

- Cible surveillée : **organisation — Ramy**
- Auteur : **consommateur**
- Exploitable : **True**
- Pertinence business : **directe**
- Langue : **darija_arabe**
- Sentiment : **positif** / faible / satisfaction
  - preuves : ['أشارك']
- Intentions : **tag_mention, partage_experience**
- Aspects : 
  - **experience_client** · positif · faible — preuves ['أشارك']
- Alertes : **—**

**Verdict** — remplace une seule case par `x` :

- x correcte
- [ ] acceptable, nuance discutable
- [ ] INCORRECTE

Si incorrecte, dis en une ligne ce qui devrait changer :

> 

---

## 4. `v02_0162`

```text
الإجابة الصحيحة هي 50 قرعة حمام محمد غيمة' 'ﮮ Zaki Zaki Hamam أم رغد
```

- Cible surveillée : **organisation — Ramy**
- Auteur : **consommateur**
- Exploitable : **True**
- Pertinence business : **directe**
- Langue : **arabe_msa**
- Sentiment : **neutre** / faible / aucune
  - preuves : —
- Intentions : **tag_mention, partage_experience**
- Aspects : **—**
- Alertes : **—**

**Verdict** — remplace une seule case par `x` :

- x correcte
- [ ] acceptable, nuance discutable
- [ ] INCORRECTE

Si incorrecte, dis en une ligne ce qui devrait changer :

> 

---

## 5. `v02_0161`

```text
لا يوجد ابتسامة ولا يوجد ضحكة انها بكل بالساطة سامطة ومتعجبش
```

- Cible surveillée : **espace_public**
- Auteur : **consommateur**
- Exploitable : **True**
- Pertinence business : **indirecte**
- Langue : **arabe_msa**
- Sentiment : **negatif** / moyenne / deception
  - preuves : ['سامطة ومتعجبش']
- Intentions : **avis, plainte**
- Aspects : 
  - **communication_information** · negatif · moyenne — preuves ['سامطة ومتعجبش']
- Alertes : **—**

**Verdict** — remplace une seule case par `x` :

- x correcte
- [ ] acceptable, nuance discutable
- [ ] INCORRECTE

Si incorrecte, dis en une ligne ce qui devrait changer :

> 

---

## 6. `v02_0299`

```text
أنا لاأحترم لي قرار والقرار الأول والأخير يعود لي ياو منحكمش الدار ومنديرش الحجر ومنديرش البافات وكل واحد مسؤول على روحو زعما دكا بانتلهم يخمو في الشعب ياو طز
```

- Cible surveillée : **espace_public**
- Auteur : **consommateur**
- Exploitable : **True**
- Pertinence business : **indirecte**
- Langue : **darija_arabe**
- Sentiment : **negatif** / forte / colere
  - preuves : ['أنا لاأحترم لي قرار', 'طز']
- Intentions : **plainte, avis**
- Aspects : 
  - **securite_conformite** · negatif · forte — preuves ['أنا لاأحترم لي قرار']
- Alertes : **—**

**Verdict** — remplace une seule case par `x` :
- x  correcte
- [ ] acceptable, nuance discutable
- [ ] INCORRECTE

Si incorrecte, dis en une ligne ce qui devrait changer :

> 

---

## 7. `v02_0254`

```text
اشواق ربی یوفقک تستاھلی یا شطورۃ🌷
```

- Cible surveillée : **espace_public**
- Auteur : **consommateur**
- Exploitable : **False** (hors_sujet)
- Pertinence business : **aucune**
- Langue : **darija_arabe**
- Sentiment : **neutre** / faible / aucune
  - preuves : —
- Intentions : **autre**
- Aspects : **—**
- Alertes : **—**

**Verdict** — remplace une seule case par `x` :

- [ ] correcte
- x  acceptable, nuance discutable
- [ ] INCORRECTE

Si incorrecte, dis en une ligne ce qui devrait changer :

> 

---

## 8. `v02_0168`

```text
Rupture de stock trop fréquente chez moi (#8604)
```

- Cible surveillée : **organisation — YaghurtPlus**
- Auteur : **consommateur**
- Exploitable : **True**
- Pertinence business : **directe**
- Langue : **francais**
- Sentiment : **negatif** / moyenne / frustration
  - preuves : ['Rupture de stock trop fréquente']
- Intentions : **plainte, signalement_incident**
- Aspects : 
  - **disponibilite_acces** · negatif · moyenne — preuves ['Rupture de stock trop fréquente']
- Alertes : 
  - **rupture_stock** · moyenne — preuves ['Rupture de stock trop fréquente']

**Verdict** — remplace une seule case par `x` :

- x correcte
- [ ] acceptable, nuance discutable
- [ ] INCORRECTE

Si incorrecte, dis en une ligne ce qui devrait changer :

> 

---

## 9. `v02_0195`

```text
بالهواء و الريح كرهنا الهدرة
```

- Cible surveillée : **espace_public**
- Auteur : **consommateur**
- Exploitable : **True**
- Pertinence business : **indirecte**
- Langue : **darija_arabe**
- Sentiment : **negatif** / moyenne / frustration
  - preuves : ['كرهنا الهدرة']
- Intentions : **plainte**
- Aspects : 
  - **communication_information** · negatif · moyenne — preuves ['كرهنا الهدرة']
- Alertes : **—**

**Verdict** — remplace une seule case par `x` :

- x correcte
- [ ] acceptable, nuance discutable
- [ ] INCORRECTE

Si incorrecte, dis en une ligne ce qui devrait changer :

> 

---

## 10. `v02_0092`

```text
هذاكاهوالمدير
```

- Cible surveillée : **espace_public**
- Auteur : **consommateur**  · contexte parent requis
- Exploitable : **False** (hors_sujet)
- Pertinence business : **aucune**
- Langue : **darija_arabe**
- Sentiment : **neutre** / faible / aucune
  - preuves : —
- Intentions : **autre**
- Aspects : **—**
- Alertes : **—**

**Verdict** — remplace une seule case par `x` :

- x correcte
- [ ] acceptable, nuance discutable
- [ ] INCORRECTE

Si incorrecte, dis en une ligne ce qui devrait changer :

> 

---

## 11. `v02_0023`

```text
حنان غا ❤️
```

- Cible surveillée : **organisation — Hamoud Boualem**
- Auteur : **consommateur**
- Exploitable : **False** (hors_sujet)
- Pertinence business : **aucune**
- Langue : **darija_arabe**
- Sentiment : **neutre** / faible / aucune
  - preuves : —
- Intentions : **—**
- Aspects : **—**
- Alertes : **—**

**Verdict** — remplace une seule case par `x` :

- x correcte
- [ ] acceptable, nuance discutable
- [ ] INCORRECTE

Si incorrecte, dis en une ligne ce qui devrait changer :

> 

---

## 12. `v02_0169`

```text
وعلاش مكانش عند اوريدو شريحة تبقى الأنترنات التردد المنخفض بعد نفاذ الجيڨات
```

- Cible surveillée : **espace_public**
- Auteur : **consommateur**
- Exploitable : **True**
- Pertinence business : **indirecte**
- Langue : **darija_arabe**
- Sentiment : **negatif** / moyenne / frustration
  - preuves : ['وعلاش مكانش عند اوريدو']
- Intentions : **suggestion, plainte, question**
- Aspects : 
  - **digital_technologie** · negatif · moyenne — preuves ['الأنترنات التردد المنخفض بعد نفاذ الجيڨات']
- Alertes : **—**

**Verdict** — remplace une seule case par `x` :

- [ ] correcte
- x  acceptable, nuance discutable
- [ ] INCORRECTE

Si incorrecte, dis en une ligne ce qui devrait changer :

> 

---

## 13. `v02_0147`

```text
لقاو انبوب السقي مربوط بالصرف الصحي
```

- Cible surveillée : **organisation — Ramy**
- Auteur : **consommateur**
- Exploitable : **True**
- Pertinence business : **directe**
- Langue : **darija_arabe**
- Sentiment : **negatif** / forte / degout
  - preuves : ['انبوب السقي مربوط بالصرف الصحي']
- Intentions : **signalement_incident, plainte**
- Aspects : 
  - **securite_conformite** · negatif · forte — preuves ['انبوب السقي مربوط بالصرف الصحي']
- Alertes : 
  - **securite_sante** · elevee — preuves ['انبوب السقي مربوط بالصرف الصحي']

**Verdict** — remplace une seule case par `x` :

- x correcte
- [ ] acceptable, nuance discutable
- [ ] INCORRECTE

Si incorrecte, dis en une ligne ce qui devrait changer :

> 

---

## 14. `v02_0107`

```text
كاش بيدون زيت رانا تبردينا في الجزائر الجديدة
```

- Cible surveillée : **espace_public**
- Auteur : **consommateur**
- Exploitable : **True**
- Pertinence business : **indirecte**
- Langue : **darija_arabe**
- Sentiment : **negatif** / moyenne / frustration  · sarcasme
  - preuves : ['كاش بيدون زيت رانا تبردينا']
- Intentions : **plainte, question**
- Aspects : 
  - **disponibilite_acces** · negatif · moyenne — preuves ['كاش بيدون زيت']
- Alertes : **—**

**Verdict** — remplace une seule case par `x` :

- [ ] correcte
- x  acceptable, nuance discutable
- [ ] INCORRECTE

Si incorrecte, dis en une ligne ce qui devrait changer :

> il ;qnaue lqletr de disponbiliter 

---

## 15. `v02_0190`

```text
Hamoud Boualem نعم. في السوبيرات الكبيرة موجود. لكن عند التجار الصغار غير موجود. لكنني سأحاول الحصول عليها. لأنني استهلك منتوجاتكم بقوة وأنا أحبها. صحا فطوركم وتقبل الله منا ومنكم 🤲
```

- Cible surveillée : **organisation — Hamoud Boualem**
- Auteur : **consommateur**
- Exploitable : **True**
- Pertinence business : **directe**
- Langue : **arabe_msa**
- Sentiment : **mixte** / moyenne / satisfaction
  - preuves : ['عند التجار الصغار غير موجود', 'استهلك منتوجاتكم بقوة وأنا أحبها']
- Intentions : **partage_experience, plainte, eloge**
- Aspects : 
  - **disponibilite_acces** · negatif · moyenne — preuves ['عند التجار الصغار غير موجود']
  - **confiance_reputation** · positif · forte — preuves ['استهلك منتوجاتكم بقوة وأنا أحبها']
- Alertes : **—**

**Verdict** — remplace une seule case par `x` :

- x correcte
- [ ] acceptable, nuance discutable
- [ ] INCORRECTE

Si incorrecte, dis en une ligne ce qui devrait changer :

> 

---

## 16. `v02_0302`

```text
رفع الله مقامكم 🌸💜🌸💜🙏🏼كما رفع السماء وتقبل منكم الصلاة والدعاء ووسع رزقكم عدد منازل وطوي صحائف اعمالكم نقيه بيضاء🙏🏼🌸💜🌸⚛🌸💜- اللهُم خاطراً طيّباً ونفساً هنيّة وصدراً راضياً مرضياً، وقلباً حامداً صابراً قوياً. ـــــــــــــــــــ 🍃🌹🍃 ــــــــــــــــــ
```

- Cible surveillée : **organisation — Hamoud Boualem**
- Auteur : **consommateur**
- Exploitable : **False** (hors_sujet)
- Pertinence business : **aucune**
- Langue : **arabe_msa**
- Sentiment : **neutre** / faible / aucune
  - preuves : —
- Intentions : **—**
- Aspects : **—**
- Alertes : **—**

**Verdict** — remplace une seule case par `x` :

- x correcte
- [ ] acceptable, nuance discutable
- [ ] INCORRECTE

Si incorrecte, dis en une ligne ce qui devrait changer :

> 

---

## 17. `v02_0228`

```text
Bayna ta3 zdjadj
```

- Cible surveillée : **organisation — Hamoud Boualem**
- Auteur : **consommateur**
- Exploitable : **True**
- Pertinence business : **directe**
- Langue : **darija_arabizi**
- Sentiment : **positif** / moyenne / satisfaction
  - preuves : ['Bayna ta3 zdjadj']
- Intentions : **eloge, avis**
- Aspects : 
  - **produit_service** · positif · moyenne — preuves ['ta3 zdjadj']
- Alertes : **—**

**Verdict** — remplace une seule case par `x` :

- [ ] correcte
- x acceptable, nuance discutable
- [ ] INCORRECTE

Si incorrecte, dis en une ligne ce qui devrait changer :

> 

---

## 18. `v02_0284`

```text
في العاصمة عندهم مستشفى و معندهمش الأراضي و في الصحراء عندهم الأراضي و معندهمش مستشفى
```

- Cible surveillée : **espace_public**
- Auteur : **consommateur**
- Exploitable : **True**
- Pertinence business : **indirecte**
- Langue : **darija_arabe**
- Sentiment : **negatif** / moyenne / frustration
  - preuves : ['في الصحراء عندهم الأراضي و معندهمش مستشفى']
- Intentions : **plainte**
- Aspects : 
  - **infrastructure_service_public** · negatif · moyenne — preuves ['في الصحراء عندهم الأراضي و معندهمش مستشفى']
- Alertes : **—**

**Verdict** — remplace une seule case par `x` :

- x correcte
- [ ] acceptable, nuance discutable
- [ ] INCORRECTE

Si incorrecte, dis en une ligne ce qui devrait changer :

> 

---

## 19. `v02_0137`

```text
المغاربة 🇲🇦 اسمحولنا كاين #رامي واحد...بالتوفيق انشاء الله
```

- Cible surveillée : **organisation — Ramy**
- Auteur : **consommateur**
- Exploitable : **True**
- Pertinence business : **directe**
- Langue : **darija_arabe**
- Sentiment : **positif** / forte / admiration
  - preuves : ['كاين #رامي واحد']
- Intentions : **eloge, avis**
- Aspects : 
  - **confiance_reputation** · positif · forte — preuves ['كاين #رامي واحد']
- Alertes : **—**

**Verdict** — remplace une seule case par `x` :

- x correcte
- [ ] acceptable, nuance discutable
- [ ] INCORRECTE

Si incorrecte, dis en une ligne ce qui devrait changer :

> 

---

## 20. `v02_0120`

```text
Chofo hedik terma gedechh yasmine tli9 pornstar 🔥🔥💦💦💦 vraiment je suis dessus ( kanet l'esti7mar n'2 ) dyroha tf1 c mieux
```

- Cible surveillée : **espace_public**
- Auteur : **consommateur**
- Exploitable : **False** (spam)
- Pertinence business : **aucune**
- Langue : **darija_arabizi**
- Sentiment : **neutre** / faible / aucune
  - preuves : —
- Intentions : **—**
- Aspects : **—**
- Alertes : **—**

**Verdict** — remplace une seule case par `x` :

- [ ] correcte
- x acceptable, nuance discutable
- [ ] INCORRECTE

Si incorrecte, dis en une ligne ce qui devrait changer :

> harcellement contenue sexeul 

---

## 21. `v02_0157`

```text
ya3jaz lisane 3ib 3IB 3IB 3IB 3IB
```

- Cible surveillée : **espace_public**
- Auteur : **consommateur**  · contexte parent requis
- Exploitable : **True**
- Pertinence business : **indirecte**
- Langue : **darija_arabizi**
- Sentiment : **neutre** / faible / aucune
  - preuves : —
- Intentions : **plainte**
- Aspects : **—**
- Alertes : **—**

**Verdict** — remplace une seule case par `x` :

- [ ] correcte
- [ ] acceptable, nuance discutable
- x INCORRECTE

Si incorrecte, dis en une ligne ce qui devrait changer :

> 
sentiement negative tres negative 
---

## 22. `v02_0231`

```text
سليسموا نتاع الماء مخلط مع ماء الصرف الصحي لي تسقي بيها المزرعة @إشارة
```

- Cible surveillée : **organisation — Ramy**
- Auteur : **consommateur**
- Exploitable : **True**
- Pertinence business : **directe**
- Langue : **darija_arabe**
- Sentiment : **negatif** / forte / degout
  - preuves : ['مخلط مع ماء الصرف الصحي لي تسقي بيها المزرعة']
- Intentions : **signalement_incident, tag_mention**
- Aspects : 
  - **securite_conformite** · negatif · forte — preuves ['مخلط مع ماء الصرف الصحي لي تسقي بيها المزرعة']
- Alertes : 
  - **securite_sante** · critique — preuves ['مخلط مع ماء الصرف الصحي لي تسقي بيها المزرعة']

**Verdict** — remplace une seule case par `x` :

- x correcte
- [ ] acceptable, nuance discutable
- [ ] INCORRECTE

Si incorrecte, dis en une ligne ce qui devrait changer :

> 

---

## 23. `v02_0259`

```text
Service client inexistant quand j'ai eu un problème (#3669)
```

- Cible surveillée : **organisation — YaghurtPlus**
- Auteur : **consommateur**
- Exploitable : **True**
- Pertinence business : **directe**
- Langue : **francais**
- Sentiment : **negatif** / forte / frustration
  - preuves : ["Service client inexistant quand j'ai eu un problème"]
- Intentions : **plainte, signalement_incident**
- Aspects : 
  - **service_client_sav** · negatif · forte — preuves ['Service client inexistant']
- Alertes : **—**

**Verdict** — remplace une seule case par `x` :

- x correcte
- [ ] acceptable, nuance discutable
- [ ] INCORRECTE

Si incorrecte, dis en une ligne ce qui devrait changer :

> 

---

## 24. `v02_0037`

```text
الف مبروك استاد دائما متميز في كثير من المجلات ربي اوفقك ان شاء الله
```

- Cible surveillée : **espace_public**
- Auteur : **consommateur**
- Exploitable : **False** (hors_sujet)
- Pertinence business : **aucune**
- Langue : **arabe_msa**
- Sentiment : **neutre** / faible / aucune
  - preuves : —
- Intentions : **—**
- Aspects : **—**
- Alertes : **—**

**Verdict** — remplace une seule case par `x` :

- x correcte
- [ ] acceptable, nuance discutable
- [ ] INCORRECTE

Si incorrecte, dis en une ligne ce qui devrait changer :

> 

---

## 25. `v02_0276`

```text
بلا إشهار نتوما الرقم الاول والصعب في المشروبات الغازية
```

- Cible surveillée : **organisation — Hamoud Boualem**
- Auteur : **consommateur**
- Exploitable : **True**
- Pertinence business : **directe**
- Langue : **arabe_msa**
- Sentiment : **positif** / forte / admiration
  - preuves : ['نتوما الرقم الاول والصعب في المشروبات الغازية']
- Intentions : **eloge, recommandation**
- Aspects : 
  - **confiance_reputation** · positif · forte — preuves ['نتوما الرقم الاول والصعب']
- Alertes : **—**

**Verdict** — remplace une seule case par `x` :

- x correcte
- [ ] acceptable, nuance discutable
- [ ] INCORRECTE

Si incorrecte, dis en une ligne ce qui devrait changer :

> 

---

## 26. `v02_0003`

```text
امين يارب العالمين
```

- Cible surveillée : **organisation — Ramy**
- Auteur : **consommateur**
- Exploitable : **False** (hors_sujet)
- Pertinence business : **aucune**
- Langue : **arabe_msa**
- Sentiment : **neutre** / faible / aucune
  - preuves : —
- Intentions : **—**
- Aspects : **—**
- Alertes : **—**

**Verdict** — remplace une seule case par `x` :

- x correcte
- [ ] acceptable, nuance discutable
- [ ] INCORRECTE

Si incorrecte, dis en une ligne ce qui devrait changer :

> 

---

## 27. `v02_0019`

```text
شبيهاا كونيكسيو هاد اليامات
```

- Cible surveillée : **espace_public**
- Auteur : **consommateur**
- Exploitable : **True**
- Pertinence business : **indirecte**
- Langue : **darija_arabe**
- Sentiment : **negatif** / moyenne / frustration
  - preuves : ['شبيهاا كونيكسيو هاد اليامات']
- Intentions : **plainte, question**
- Aspects : 
  - **digital_technologie** · negatif · moyenne — preuves ['شبيهاا كونيكسيو هاد اليامات']
- Alertes : **—**

**Verdict** — remplace une seule case par `x` :

- x correcte
- [ ] acceptable, nuance discutable
- [ ] INCORRECTE

Si incorrecte, dis en une ligne ce qui devrait changer :

> 

---

## 28. `v02_0248`

```text
عندي 207 سيري 2012 hd 1.6 زعم شحال تجيبلي ومفيهاش عواده
```

- Cible surveillée : **espace_public**
- Auteur : **consommateur**
- Exploitable : **True**
- Pertinence business : **indirecte**
- Langue : **darija_arabe**
- Sentiment : **neutre** / faible / aucune
  - preuves : —
- Intentions : **question, demande_information**
- Aspects : 
  - **prix_valeur** · positif · faible — preuves ['شحال تجيبلي']
- Alertes : **—**

**Verdict** — remplace une seule case par `x` :

- x correcte
- [ ] acceptable, nuance discutable
- [ ] INCORRECTE

Si incorrecte, dis en une ligne ce qui devrait changer :

> 

---

## 29. `v02_0128`

```text
كي نشريه من فرنك دايما يكون طازج (#2663)
```

- Cible surveillée : **organisation — YaghurtPlus**
- Auteur : **consommateur**
- Exploitable : **True**
- Pertinence business : **directe**
- Langue : **darija_arabe**
- Sentiment : **positif** / forte / satisfaction
  - preuves : ['دايما يكون طازج']
- Intentions : **eloge, avis**
- Aspects : 
  - **produit_service** · positif · forte — preuves ['دايما يكون طازج']
- Alertes : **—**

**Verdict** — remplace une seule case par `x` :

- x correcte
- [ ] acceptable, nuance discutable
- [ ] INCORRECTE

Si incorrecte, dis en une ligne ce qui devrait changer :

> 

---

## 30. `v02_0081`

```text
الحمد لله راني ب 3g 😌😌
```

- Cible surveillée : **espace_public**
- Auteur : **consommateur**
- Exploitable : **True**
- Pertinence business : **indirecte**
- Langue : **darija_arabizi**
- Sentiment : **positif** / moyenne / satisfaction
  - preuves : ['الحمد لله راني ب 3g']
- Intentions : **partage_experience**
- Aspects : 
  - **digital_technologie** · positif · moyenne — preuves ['راني ب 3g']
- Alertes : **—**

**Verdict** — remplace une seule case par `x` :

- [ ] correcte
- x acceptable, nuance discutable
- [ ] INCORRECTE

Si incorrecte, dis en une ligne ce qui devrait changer :

> 

---

## 31. `v02_0126`

```text
على اي اساس يتم توظيف هؤلاء في مجال الإعلام والصحافة؟؟ومامحل خريجي جامعات الإعلام والاتصال من الإعراب.مفارقة عجيبة وغريبة .ولكن في الجزائر تلقاها ممثلة منشطة مقدمة و و .
```

- Cible surveillée : **espace_public**
- Auteur : **consommateur**
- Exploitable : **True**
- Pertinence business : **indirecte**
- Langue : **arabe_msa**
- Sentiment : **negatif** / forte / colere
  - preuves : ['على اي اساس يتم توظيف هؤلاء في مجال الإعلام والصحافة']
- Intentions : **plainte, question**
- Aspects : 
  - **emploi_management** · negatif · forte — preuves ['على اي اساس يتم توظيف هؤلاء']
- Alertes : **—**

**Verdict** — remplace une seule case par `x` :

- x  correcte
- [ ] acceptable, nuance discutable
- [ ] INCORRECTE

Si incorrecte, dis en une ligne ce qui devrait changer :

> 

---

## 32. `v02_0030`

```text
لقاوها تسقي بالصرف الصحي الزيقو🤢 حاشاكم في بلاصة الماء
```

- Cible surveillée : **organisation — Ramy**
- Auteur : **consommateur**
- Exploitable : **True**
- Pertinence business : **directe**
- Langue : **darija_arabe**
- Sentiment : **negatif** / forte / degout
  - preuves : ['لقاوها تسقي بالصرف الصحي الزيقو🤢']
- Intentions : **signalement_incident, plainte**
- Aspects : 
  - **securite_conformite** · negatif · forte — preuves ['لقاوها تسقي بالصرف الصحي الزيقو🤢']
- Alertes : 
  - **securite_sante** · critique — preuves ['لقاوها تسقي بالصرف الصحي الزيقو🤢']

**Verdict** — remplace une seule case par `x` :

- x correcte
- [ ] acceptable, nuance discutable
- [ ] INCORRECTE

Si incorrecte, dis en une ligne ce qui devrait changer :

> 

---

## 33. `v02_0097`

```text
Waouw quelle fraîcheur, je recommande vivement (#6224)
```

- Cible surveillée : **organisation — YaghurtPlus**
- Auteur : **consommateur**
- Exploitable : **True**
- Pertinence business : **directe**
- Langue : **francais**
- Sentiment : **positif** / forte / satisfaction
  - preuves : ['quelle fraîcheur', 'je recommande vivement']
- Intentions : **eloge, recommandation, avis**
- Aspects : 
  - **produit_service** · positif · forte — preuves ['quelle fraîcheur']
  - **confiance_reputation** · positif · forte — preuves ['je recommande vivement']
- Alertes : **—**

**Verdict** — remplace une seule case par `x` :

- x correcte
- [ ] acceptable, nuance discutable
- [ ] INCORRECTE

Si incorrecte, dis en une ligne ce qui devrait changer :

> 

---

## 34. `v02_0065`

```text
Rani nebgha had lya9hourt, tay3jebni bzzaf (#7584)
```

- Cible surveillée : **organisation — YaghurtPlus**
- Auteur : **consommateur**
- Exploitable : **True**
- Pertinence business : **directe**
- Langue : **darija_arabizi**
- Sentiment : **positif** / forte / satisfaction
  - preuves : ['Rani nebgha had lya9hourt', 'tay3jebni bzzaf']
- Intentions : **eloge, avis**
- Aspects : 
  - **produit_service** · positif · forte — preuves ['tay3jebni bzzaf']
  - **experience_client** · positif · forte — preuves ['Rani nebgha had lya9hourt']
- Alertes : **—**

**Verdict** — remplace une seule case par `x` :

- x correcte
- [ ] acceptable, nuance discutable
- [ ] INCORRECTE

Si incorrecte, dis en une ligne ce qui devrait changer :

> 

---

## 35. `v02_0199`

```text
الف مبروك للفائزين والله يرزقنا معاهم يا رب والف تحية للمنتج على المصداقية ❣️🫡
```

- Cible surveillée : **organisation — Hamoud Boualem**
- Auteur : **consommateur**
- Exploitable : **True**
- Pertinence business : **directe**
- Langue : **arabe_msa**
- Sentiment : **positif** / forte / confiance
  - preuves : ['الف تحية للمنتج على المصداقية']
- Intentions : **eloge, partage_experience**
- Aspects : 
  - **confiance_reputation** · positif · forte — preuves ['تحية للمنتج على المصداقية']
- Alertes : **—**

**Verdict** — remplace une seule case par `x` :

- x correcte
- [ ] acceptable, nuance discutable
- [ ] INCORRECTE

Si incorrecte, dis en une ligne ce qui devrait changer :

> 

---

## 36. `v02_0112`

```text
الراعي الرسمي في المائدة الجزائرية
```

- Cible surveillée : **organisation — Hamoud Boualem**
- Auteur : **consommateur**
- Exploitable : **True**
- Pertinence business : **directe**
- Langue : **arabe_msa**
- Sentiment : **positif** / forte / admiration
  - preuves : ['الراعي الرسمي في المائدة الجزائرية']
- Intentions : **eloge, avis**
- Aspects : 
  - **confiance_reputation** · positif · forte — preuves ['الراعي الرسمي في المائدة الجزائرية']
- Alertes : **—**

**Verdict** — remplace une seule case par `x` :

- x correcte
- [ ] acceptable, nuance discutable
- [ ] INCORRECTE

Si incorrecte, dis en une ligne ce qui devrait changer :

> 

---

## 37. `v02_0212`

```text
انشاء الله يكون من نصبي
```

- Cible surveillée : **organisation — Hamoud Boualem**
- Auteur : **consommateur**
- Exploitable : **True**
- Pertinence business : **directe**
- Langue : **darija_arabe**
- Sentiment : **positif** / faible / aucune
  - preuves : ['يكون من نصبي']
- Intentions : **partage_experience**
- Aspects : 
  - **experience_client** · positif · faible — preuves ['يكون من نصبي']
- Alertes : **—**

**Verdict** — remplace une seule case par `x` :

- [ ] correcte
- [ ] acceptable, nuance discutable
- x INCORRECTE

Si incorrecte, dis en une ligne ce qui devrait changer :

> neutre 

---

## 38. `v02_0179`

```text
Ya3tikoum saha 👌 L moussi9a Talya ta3 chi3r kissamouh ?
```

- Cible surveillée : **espace_public**
- Auteur : **consommateur**
- Exploitable : **True**
- Pertinence business : **indirecte**
- Langue : **darija_arabizi**
- Sentiment : **positif** / faible / satisfaction
  - preuves : ['Ya3tikoum saha']
- Intentions : **question, demande_information, eloge**
- Aspects : 
  - **communication_information** · positif · faible — preuves ['Ya3tikoum saha']
- Alertes : **—**

**Verdict** — remplace une seule case par `x` :

- x correcte
- [ ] acceptable, nuance discutable
- [ ] INCORRECTE

Si incorrecte, dis en une ligne ce qui devrait changer :

> 

---

## 39. `v02_0208`

```text
Hamoud Boualem salam le code qr est bloque jaraive pas a ouvrir merci
```

- Cible surveillée : **organisation — Hamoud Boualem**
- Auteur : **consommateur**
- Exploitable : **True**
- Pertinence business : **directe**
- Langue : **francais**
- Sentiment : **negatif** / moyenne / frustration
  - preuves : ['le code qr est bloque jaraive pas a ouvrir']
- Intentions : **demande_aide, signalement_incident**
- Aspects : 
  - **digital_technologie** · negatif · moyenne — preuves ['le code qr est bloque jaraive pas a ouvrir']
- Alertes : **—**

**Verdict** — remplace une seule case par `x` :

- x correcte
- [ ] acceptable, nuance discutable
- [ ] INCORRECTE

Si incorrecte, dis en une ligne ce qui devrait changer :

> jsp si il faut une alerts ici 

---

## 40. `v02_0113`

```text
بسمة الأمل عن قريب
```

- Cible surveillée : **organisation — Hamoud Boualem**
- Auteur : **consommateur**
- Exploitable : **True**
- Pertinence business : **directe**
- Langue : **arabe_msa**
- Sentiment : **positif** / moyenne / satisfaction
  - preuves : ['بسمة الأمل عن قريب']
- Intentions : **eloge**
- Aspects : 
  - **communication_information** · positif · moyenne — preuves ['بسمة الأمل عن قريب']
- Alertes : **—**

**Verdict** — remplace une seule case par `x` :

- [ ] correcte
- x acceptable, nuance discutable
- [ ] INCORRECTE

Si incorrecte, dis en une ligne ce qui devrait changer :

> 

---

## 41. `v02_0111`

```text
Machallah 3liykoum y’a allah chehal nhabkoum nhabkoum bzf ❤️❤️❤️🌹
```

- Cible surveillée : **espace_public**
- Auteur : **consommateur**
- Exploitable : **False** (hors_sujet)
- Pertinence business : **aucune**
- Langue : **darija_arabizi**
- Sentiment : **neutre** / faible / aucune
  - preuves : —
- Intentions : **autre**
- Aspects : **—**
- Alertes : **—**

**Verdict** — remplace une seule case par `x` :

- [ ] correcte
- [ ] acceptable, nuance discutable
- x INCORRECTE

Si incorrecte, dis en une ligne ce qui devrait changer :

> positive 

---

## 42. `v02_0210`

```text
Ramy Food je participe 50 قرعة رامي الجوهرة اللامعة وصہٰية الرسٰول همسة 'ﮮ والدة قدر مشا كسة عبلة الصبورة
```

- Cible surveillée : **organisation — Ramy**
- Auteur : **consommateur**
- Exploitable : **True**
- Pertinence business : **directe**
- Langue : **darija_arabe**
- Sentiment : **positif** / faible / aucune
  - preuves : ['je participe']
- Intentions : **partage_experience, tag_mention**
- Aspects : 
  - **experience_client** · positif · faible — preuves ['je participe']
- Alertes : **—**

**Verdict** — remplace une seule case par `x` :

- x correcte
- [ ] acceptable, nuance discutable
- [ ] INCORRECTE

Si incorrecte, dis en une ligne ce qui devrait changer :

> 

---

## 43. `v02_0264`

```text
Mohamed Aiouadj ❤️💙
```

- Cible surveillée : **organisation — Hamoud Boualem**
- Auteur : **consommateur**
- Exploitable : **True**
- Pertinence business : **directe**
- Langue : **autre**
- Sentiment : **positif** / faible / aucune
  - preuves : —
- Intentions : **tag_mention**
- Aspects : **—**
- Alertes : **—**

**Verdict** — remplace une seule case par `x` :

- [ ] correcte
- x acceptable, nuance discutable
- [ ] INCORRECTE

Si incorrecte, dis en une ligne ce qui devrait changer :

> 

---

## 44. `v02_0175`

```text
روعة والله الله يعطيهم الصحة و مزيد من تألق و النجاح إنشاء الله 👍😍🇩🇿✅✅✔️💪
```

- Cible surveillée : **espace_public**
- Auteur : **consommateur**
- Exploitable : **True**
- Pertinence business : **indirecte**
- Langue : **arabe_msa**
- Sentiment : **positif** / forte / admiration
  - preuves : ['روعة والله الله يعطيهم الصحة', 'مزيد من تألق و النجاح']
- Intentions : **eloge**
- Aspects : 
  - **confiance_reputation** · positif · forte — preuves ['روعة والله الله يعطيهم الصحة']
- Alertes : **—**

**Verdict** — remplace une seule case par `x` :

- x correcte
- [ ] acceptable, nuance discutable
- [ ] INCORRECTE

Si incorrecte, dis en une ligne ce qui devrait changer :

> 

---

## 45. `v02_0202`

```text
لقاو تيو تاع الماء لي يسقو بيه المزرعة مربوط مع الصرف الصحي الحياء أميرة اية الرحمان
```

- Cible surveillée : **organisation — Ramy**
- Auteur : **consommateur**
- Exploitable : **True**
- Pertinence business : **directe**
- Langue : **darija_arabe**
- Sentiment : **negatif** / forte / degout
  - preuves : ['مربوط مع الصرف الصحي']
- Intentions : **signalement_incident, tag_mention**
- Aspects : 
  - **securite_conformite** · negatif · forte — preuves ['مربوط مع الصرف الصحي']
- Alertes : 
  - **securite_sante** · critique — preuves ['مربوط مع الصرف الصحي']

**Verdict** — remplace une seule case par `x` :

- x correcte
- [ ] acceptable, nuance discutable
- [ ] INCORRECTE

Si incorrecte, dis en une ligne ce qui devrait changer :

> 

---

## 46. `v02_0287`

```text
بسم الله اشارك 50رامي قرعة Jo Jo Øům ŤõüQă سہٰلہٰسہٰبٰٰيٰلہٰ الہٰجنة
```

- Cible surveillée : **organisation — Ramy**
- Auteur : **consommateur**
- Exploitable : **True**
- Pertinence business : **directe**
- Langue : **darija_arabe**
- Sentiment : **positif** / faible / satisfaction
  - preuves : ['اشارك']
- Intentions : **tag_mention, partage_experience**
- Aspects : 
  - **experience_client** · positif · faible — preuves ['اشارك']
- Alertes : **—**

**Verdict** — remplace une seule case par `x` :

- x correcte
- [ ] acceptable, nuance discutable
- [ ] INCORRECTE

Si incorrecte, dis en une ligne ce qui devrait changer :

> 

---

## 47. `v02_0285`

```text
Pas frais à l'achat, date limite trop proche (#3214)
```

- Cible surveillée : **organisation — YaghurtPlus**
- Auteur : **consommateur**
- Exploitable : **True**
- Pertinence business : **directe**
- Langue : **francais**
- Sentiment : **negatif** / moyenne / deception
  - preuves : ["Pas frais à l'achat", 'date limite trop proche']
- Intentions : **plainte, signalement_incident**
- Aspects : 
  - **produit_service** · negatif · moyenne — preuves ["Pas frais à l'achat", 'date limite trop proche']
- Alertes : **—**

**Verdict** — remplace une seule case par `x` :

- x correcte
- [ ] acceptable, nuance discutable
- [ ] INCORRECTE

Si incorrecte, dis en une ligne ce qui devrait changer :

> 

---

## 48. `v02_0007`

```text
اسم الاغنية
```

- Cible surveillée : **organisation — Hamoud Boualem**
- Auteur : **consommateur**
- Exploitable : **True**
- Pertinence business : **directe**
- Langue : **arabe_msa**
- Sentiment : **neutre** / faible / aucune
  - preuves : —
- Intentions : **demande_information, question**
- Aspects : **—**
- Alertes : **—**

**Verdict** — remplace une seule case par `x` :

- x correcte
- [ ] acceptable, nuance discutable
- [ ] INCORRECTE

Si incorrecte, dis en une ligne ce qui devrait changer :

> 

---

## 49. `v02_0197`

```text
Mohamade Serradj 🥰🥰
```

- Cible surveillée : **organisation — Hamoud Boualem**
- Auteur : **consommateur**
- Exploitable : **True**
- Pertinence business : **directe**
- Langue : **autre**
- Sentiment : **positif** / faible / aucune
  - preuves : —
- Intentions : **tag_mention**
- Aspects : **—**
- Alertes : **—**

**Verdict** — remplace une seule case par `x` :

- [ ] correcte
- x acceptable, nuance discutable
- [ ] INCORRECTE

Si incorrecte, dis en une ligne ce qui devrait changer :

> 

---

## 50. `v02_0073`

```text
Hamoud Boualem cheit 3likom presque 20 bouteille c bon manzich g3 n amankom w ndir fikom tika
```

- Cible surveillée : **organisation — Hamoud Boualem**
- Auteur : **consommateur**
- Exploitable : **True**
- Pertinence business : **directe**
- Langue : **darija_arabizi**
- Sentiment : **negatif** / forte / colere
  - preuves : ['manzich g3 n amankom w ndir fikom tika']
- Intentions : **plainte, partage_experience**
- Aspects : 
  - **confiance_reputation** · negatif · forte — preuves ['manzich g3 n amankom w ndir fikom tika']
- Alertes : **—**

**Verdict** — remplace une seule case par `x` :

- x correcte
- [ ] acceptable, nuance discutable
- [ ] INCORRECTE

Si incorrecte, dis en une ligne ce qui devrait changer :

> 

---

## 51. `v02_0220`

```text
ما نحلف بصح مسابقة 1000% ماشي صح و ما فيها مصداقية
```

- Cible surveillée : **organisation — Hamoud Boualem**
- Auteur : **consommateur**
- Exploitable : **True**
- Pertinence business : **directe**
- Langue : **darija_arabe**
- Sentiment : **negatif** / forte / colere
  - preuves : ['مسابقة 1000% ماشي صح و ما فيها مصداقية']
- Intentions : **plainte, signalement_incident**
- Aspects : 
  - **confiance_reputation** · negatif · forte — preuves ['ما فيها مصداقية']
- Alertes : 
  - **fraude_arnaque** · elevee — preuves ['مسابقة 1000% ماشي صح و ما فيها مصداقية']

**Verdict** — remplace une seule case par `x` :

- x correcte
- [ ] acceptable, nuance discutable
- [ ] INCORRECTE

Si incorrecte, dis en une ligne ce qui devrait changer :

> 

---

## 52. `v02_0215`

```text
ya zmar rouh 3lina o mtbynch rohk rouhhhh
```

- Cible surveillée : **espace_public**
- Auteur : **consommateur**
- Exploitable : **False** (hors_sujet)
- Pertinence business : **aucune**
- Langue : **darija_arabizi**
- Sentiment : **neutre** / faible / aucune
  - preuves : —
- Intentions : **autre**
- Aspects : **—**
- Alertes : **—**

**Verdict** — remplace une seule case par `x` :

- [ ] correcte
- [ ] acceptable, nuance discutable
- x INCORRECTE

Si incorrecte, dis en une ligne ce qui devrait changer :

> sentiment negative 

---

## 53. `v02_0188`

```text
كيف احضر الدورة من المنزل
```

- Cible surveillée : **espace_public**
- Auteur : **consommateur**
- Exploitable : **True**
- Pertinence business : **indirecte**
- Langue : **arabe_msa**
- Sentiment : **neutre** / faible / aucune
  - preuves : —
- Intentions : **question, demande_information**
- Aspects : **—**
- Alertes : **—**

**Verdict** — remplace une seule case par `x` :

- x correcte
- [ ] acceptable, nuance discutable
- [ ] INCORRECTE

Si incorrecte, dis en une ligne ce qui devrait changer :

> 

---

## 54. `v02_0031`

```text
تافهين لي يضحكوا
```

- Cible surveillée : **espace_public**
- Auteur : **consommateur**  · contexte parent requis
- Exploitable : **True**
- Pertinence business : **aucune**
- Langue : **darija_arabe**
- Sentiment : **neutre** / faible / aucune
  - preuves : —
- Intentions : **avis**
- Aspects : **—**
- Alertes : **—**

**Verdict** — remplace une seule case par `x` :

- x correcte
- [ ] acceptable, nuance discutable
- [ ] INCORRECTE

Si incorrecte, dis en une ligne ce qui devrait changer :

> 

---

## 55. `v02_0180`

```text
المنافق الشيات
```

- Cible surveillée : **espace_public**
- Auteur : **consommateur**  · contexte parent requis
- Exploitable : **True**
- Pertinence business : **aucune**
- Langue : **darija_arabe**
- Sentiment : **neutre** / faible / colere
  - preuves : —
- Intentions : **plainte**
- Aspects : **—**
- Alertes : **—**

**Verdict** — remplace une seule case par `x` :

- [ ] correcte
- x acceptable, nuance discutable
- [ ] INCORRECTE

Si incorrecte, dis en une ligne ce qui devrait changer :

> 

---

## 56. `v02_0292`

```text
بصفتي خبير إقتصادي . أرىٰ أن بئر قسنطينة هو السبب في إرتفاع السعر العالمي للنفط ..  🤗
```

- Cible surveillée : **espace_public**
- Auteur : **consommateur**
- Exploitable : **True**
- Pertinence business : **indirecte**
- Langue : **arabe_msa**
- Sentiment : **neutre** / faible / aucune  · sarcasme
  - preuves : —
- Intentions : **avis**
- Aspects : **—**
- Alertes : **—**

**Verdict** — remplace une seule case par `x` :

- x correcte
- [ ] acceptable, nuance discutable
- [ ] INCORRECTE

Si incorrecte, dis en une ligne ce qui devrait changer :

> 

---

## 57. `v02_0260`

```text
Re King صحة حفظك
```

- Cible surveillée : **organisation — Hamoud Boualem**
- Auteur : **consommateur**  · contexte parent requis
- Exploitable : **True**
- Pertinence business : **directe**
- Langue : **darija_arabe**
- Sentiment : **neutre** / faible / aucune
  - preuves : —
- Intentions : **tag_mention**
- Aspects : **—**
- Alertes : **—**

**Verdict** — remplace une seule case par `x` :

- x correcte
- [ ] acceptable, nuance discutable
- [ ] INCORRECTE

Si incorrecte, dis en une ligne ce qui devrait changer :

> 

---

## 58. `v02_0085`

```text
قانون. تبق. علجمع
```

- Cible surveillée : **organisation — Ramy**
- Auteur : **consommateur**  · contexte parent requis
- Exploitable : **True**
- Pertinence business : **directe**
- Langue : **arabe_msa**
- Sentiment : **neutre** / faible / aucune
  - preuves : —
- Intentions : **avis**
- Aspects : **—**
- Alertes : **—**

**Verdict** — remplace une seule case par `x` :

- [ ] correcte
- x acceptable, nuance discutable
- [ ] INCORRECTE

Si incorrecte, dis en une ligne ce qui devrait changer :

> 

---

## 59. `v02_0101`

```text
Wallah mazalhoume 3aichine fi tes3inates
```

- Cible surveillée : **espace_public**
- Auteur : **consommateur**  · contexte parent requis
- Exploitable : **True**
- Pertinence business : **aucune**
- Langue : **darija_arabizi**
- Sentiment : **neutre** / faible / aucune
  - preuves : —
- Intentions : **avis**
- Aspects : **—**
- Alertes : **—**

**Verdict** — remplace une seule case par `x` :

- x correcte
- [ ] acceptable, nuance discutable
- [ ] INCORRECTE

Si incorrecte, dis en une ligne ce qui devrait changer :

> 

---

## 60. `v02_0258`

```text
مفهمت والو بالاك انا لي منعرفش
```

- Cible surveillée : **espace_public**
- Auteur : **consommateur**  · contexte parent requis
- Exploitable : **True**
- Pertinence business : **indirecte**
- Langue : **darija_arabe**
- Sentiment : **neutre** / faible / aucune
  - preuves : —
- Intentions : **autre**
- Aspects : **—**
- Alertes : **—**

**Verdict** — remplace une seule case par `x` :

- x correcte
- [ ] acceptable, nuance discutable
- [ ] INCORRECTE

Si incorrecte, dis en une ligne ce qui devrait changer :

> 

---
