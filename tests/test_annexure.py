from claimcheck.annexure import annexure_items

PAGES = ["", "ANNEXURE I \nList I – Optional Items \nSl \nNo \nItem \n1 BABY FOOD \n2 TELEPHONE CHARGES \n3 EXTRA DIET OF PATIENT (OTHER THAN THAT WHICH FORMS PART OF \nBED CHARGE) \n",
         "2. Where the costs are to be subsumed into the room charges \nList II – Items that are to be subsumed into Room Charges \n4 PELVIC TRACTION BELT \n5 VASOFIX SAFETY \nSl \n1 BABY CHARGES (UNLESS SPECIFIED/INDICATED) \n2 HAND WASH \n",
         "List III – Items \n3 SPUTUM CUP \n1 HAIR REMOVAL CREAM \n2 EYE PAD \n1 ADMISSION/REGISTRATION CHARGES \n2 URINE BAG \nANNEXURE II \n7 OTHER"]


def test_interleaved_lists():
    it = annexure_items(PAGES)
    got = [(c["list_no"], c["section"].split()[-1], c["content"].split(": item ")[1]) for c in it]
    assert got == [(1, "1", "1. BABY FOOD"), (1, "2", "2. TELEPHONE CHARGES"),
                   (1, "3", "3. EXTRA DIET OF PATIENT (OTHER THAN THAT WHICH FORMS PART OF BED CHARGE)"),
                   (1, "4", "4. PELVIC TRACTION BELT"), (1, "5", "5. VASOFIX SAFETY"),
                   (2, "1", "1. BABY CHARGES (UNLESS SPECIFIED/INDICATED)"), (2, "2", "2. HAND WASH"), (2, "3", "3. SPUTUM CUP"),
                   (3, "1", "1. HAIR REMOVAL CREAM"), (3, "2", "2. EYE PAD"), (4, "1", "1. ADMISSION/REGISTRATION CHARGES"), (4, "2", "2. URINE BAG")]
