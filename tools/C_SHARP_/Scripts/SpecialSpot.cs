using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.EventSystems;

public class SpecialSpot : MonoBehaviour, IPointerEnterHandler, IPointerExitHandler
{
    PlayerInventory inventoryManager;
    public Item item;
    public string filterTag;
    void Start()
    {
        inventoryManager = GameObject.Find("Player").GetComponent<PlayerInventory>();
    }
    public void OnPointerEnter(PointerEventData eventData)
    {
        inventoryManager.mouseSpecialEnter(this);
    }
    public void OnPointerExit(PointerEventData eventData)
    {
        inventoryManager.mouseSpecialExit(this);
    }
}
